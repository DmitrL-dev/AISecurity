//! Certificate Authority for TLS inspection
//!
//! Generates and manages SENTINEL Root CA and per-site certificates.

use rcgen::{
    BasicConstraints, CertificateParams, DistinguishedName, DnType, 
    ExtendedKeyUsagePurpose, IsCa, KeyPair, KeyUsagePurpose, SanType,
    Certificate,
};
use rustls::pki_types::{CertificateDer, PrivateKeyDer, PrivatePkcs8KeyDer};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use std::sync::RwLock;
use tracing::info;

/// Certificate Authority for generating site certificates
pub struct CertificateAuthority {
    /// CA certificate (DER)
    ca_cert_der: CertificateDer<'static>,
    /// CA certificate (for signing)
    ca_cert: Certificate,
    /// CA private key
    ca_key: KeyPair,
    /// Cache of generated site certificates (cert DER, key DER)
    cert_cache: RwLock<HashMap<String, (Vec<u8>, Vec<u8>)>>,
    /// Storage path
    storage_path: PathBuf,
}

impl CertificateAuthority {
    /// Create or load CA from storage
    pub fn new(storage_path: PathBuf) -> Result<Self, Box<dyn std::error::Error + Send + Sync>> {
        fs::create_dir_all(&storage_path)?;
        
        let ca_cert_path = storage_path.join("sentinel-ca.crt");
        let ca_key_path = storage_path.join("sentinel-ca.key");
        
        let (ca_cert_der, ca_cert, ca_key) = if ca_cert_path.exists() && ca_key_path.exists() {
            info!("Loading existing SENTINEL CA");
            Self::load_ca(&ca_cert_path, &ca_key_path)?
        } else {
            info!("Generating new SENTINEL CA");
            Self::generate_ca(&ca_cert_path, &ca_key_path)?
        };
        
        Ok(Self {
            ca_cert_der,
            ca_cert,
            ca_key,
            cert_cache: RwLock::new(HashMap::new()),
            storage_path,
        })
    }
    
    /// Generate new CA certificate
    fn generate_ca(
        cert_path: &PathBuf,
        key_path: &PathBuf,
    ) -> Result<(CertificateDer<'static>, Certificate, KeyPair), Box<dyn std::error::Error + Send + Sync>> {
        let mut params = CertificateParams::default();
        
        // Set CA distinguished name
        let mut dn = DistinguishedName::new();
        dn.push(DnType::CommonName, "SENTINEL Security CA");
        dn.push(DnType::OrganizationName, "SENTINEL");
        dn.push(DnType::CountryName, "RU");
        params.distinguished_name = dn;
        
        // CA settings
        params.is_ca = IsCa::Ca(BasicConstraints::Unconstrained);
        params.key_usages = vec![
            KeyUsagePurpose::KeyCertSign,
            KeyUsagePurpose::CrlSign,
            KeyUsagePurpose::DigitalSignature,
        ];
        
        // Valid for 10 years
        params.not_before = time::OffsetDateTime::now_utc();
        params.not_after = params.not_before + time::Duration::days(3650);
        
        // Generate key pair
        let key_pair = KeyPair::generate()?;
        
        // Self-sign
        let cert = params.self_signed(&key_pair)?;
        
        // Save to files
        fs::write(cert_path, cert.pem())?;
        fs::write(key_path, key_pair.serialize_pem())?;
        
        info!("SENTINEL CA generated and saved");
        
        let cert_der = CertificateDer::from(cert.der().to_vec());
        
        Ok((cert_der, cert, key_pair))
    }
    
    /// Load existing CA from files
    fn load_ca(
        cert_path: &PathBuf,
        key_path: &PathBuf,
    ) -> Result<(CertificateDer<'static>, Certificate, KeyPair), Box<dyn std::error::Error + Send + Sync>> {
        let cert_pem = fs::read_to_string(cert_path)?;
        let key_pem = fs::read_to_string(key_path)?;
        
        let key_pair = KeyPair::from_pem(&key_pem)?;
        
        // Parse PEM to DER
        let cert_der = {
            let mut reader = std::io::BufReader::new(cert_pem.as_bytes());
            let certs = rustls_pemfile::certs(&mut reader).collect::<Result<Vec<_>, _>>()?;
            certs.into_iter().next().ok_or("No certificate found")?
        };
        
        // Recreate CA certificate for signing
        let mut params = CertificateParams::default();
        let mut dn = DistinguishedName::new();
        dn.push(DnType::CommonName, "SENTINEL Security CA");
        dn.push(DnType::OrganizationName, "SENTINEL");
        params.distinguished_name = dn;
        params.is_ca = IsCa::Ca(BasicConstraints::Unconstrained);
        params.key_usages = vec![
            KeyUsagePurpose::KeyCertSign,
            KeyUsagePurpose::CrlSign,
            KeyUsagePurpose::DigitalSignature,
        ];
        
        let ca_cert = params.self_signed(&key_pair)?;
        
        Ok((cert_der, ca_cert, key_pair))
    }
    
    /// Generate certificate for a specific host
    pub fn generate_cert_for_host(
        &self,
        host: &str,
    ) -> Result<(CertificateDer<'static>, PrivateKeyDer<'static>), Box<dyn std::error::Error + Send + Sync>> {
        // Check cache
        {
            let cache = self.cert_cache.read().unwrap();
            if let Some((cert_bytes, key_bytes)) = cache.get(host) {
                let cert = CertificateDer::from(cert_bytes.clone());
                let key = PrivateKeyDer::Pkcs8(PrivatePkcs8KeyDer::from(key_bytes.clone()));
                return Ok((cert, key));
            }
        }
        
        // Generate new cert
        let mut params = CertificateParams::default();
        
        let mut dn = DistinguishedName::new();
        dn.push(DnType::CommonName, host);
        params.distinguished_name = dn;
        
        // Server certificate settings
        params.is_ca = IsCa::NoCa;
        params.key_usages = vec![
            KeyUsagePurpose::DigitalSignature,
            KeyUsagePurpose::KeyEncipherment,
        ];
        params.extended_key_usages = vec![ExtendedKeyUsagePurpose::ServerAuth];
        
        // Add host as SAN
        params.subject_alt_names = vec![SanType::DnsName(host.try_into()?)];
        
        // Valid for 1 year
        params.not_before = time::OffsetDateTime::now_utc();
        params.not_after = params.not_before + time::Duration::days(365);
        
        // Generate key pair for this cert
        let key_pair = KeyPair::generate()?;
        
        // Sign with CA
        let cert = params.signed_by(&key_pair, &self.ca_cert, &self.ca_key)?;
        
        let cert_bytes = cert.der().to_vec();
        let key_bytes = key_pair.serialize_der();
        
        let cert_der = CertificateDer::from(cert_bytes.clone());
        let key_der = PrivateKeyDer::Pkcs8(PrivatePkcs8KeyDer::from(key_bytes.clone()));
        
        // Cache it
        {
            let mut cache = self.cert_cache.write().unwrap();
            cache.insert(host.to_string(), (cert_bytes, key_bytes));
        }
        
        Ok((cert_der, key_der))
    }
    
    /// Get CA certificate for installation
    pub fn get_ca_cert(&self) -> &CertificateDer<'static> {
        &self.ca_cert_der
    }
    
    /// Get CA certificate path for user installation
    pub fn get_ca_cert_path(&self) -> PathBuf {
        self.storage_path.join("sentinel-ca.crt")
    }
}
