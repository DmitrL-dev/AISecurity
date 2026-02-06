//! Shadow LLM Scanner - Network fingerprinting for exposed AI services
//!
//! Detects Ollama, vLLM, TGI, LangServe and other LLM platforms.

mod fingerprint;
mod probe;
mod sweep;

use clap::{Parser, Subcommand};
use std::error::Error;

#[derive(Parser)]
#[command(name = "sentinel-scan")]
#[command(about = "Shadow LLM Scanner - Detect exposed AI services")]
#[command(version)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Probe a single target for LLM services
    Probe {
        /// Target URL (e.g., http://localhost:11434)
        target: String,
        
        /// Timeout in seconds
        #[arg(short, long, default_value = "3")]
        timeout: u64,
    },
    
    /// Sweep a network range for LLM services
    Sweep {
        /// CIDR range (e.g., 192.168.1.0/24)
        range: String,
        
        /// Port to scan
        #[arg(short, long, default_value = "11434")]
        port: u16,
        
        /// Max concurrent connections
        #[arg(short, long, default_value = "50")]
        concurrency: usize,
    },
    
    /// Enumerate models on a target
    Enum {
        /// Target URL
        target: String,
    },
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let cli = Cli::parse();
    
    match cli.command {
        Commands::Probe { target, timeout } => {
            let result = fingerprint::probe_target(&target, timeout).await?;
            match result {
                Some(platform) => println!("✅ Detected: {}", platform),
                None => println!("❌ No LLM service detected"),
            }
        }
        Commands::Sweep { range, port, concurrency } => {
            let results = sweep::scan_range(&range, port, concurrency).await?;
            println!("{}", serde_json::to_string_pretty(&results)?);
        }
        Commands::Enum { target } => {
            let models = fingerprint::enumerate_models(&target).await?;
            for model in models {
                println!("📦 {}", model);
            }
        }
    }
    
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_cli_parses() {
        // Verify CLI struct can be created
        use clap::CommandFactory;
        Cli::command().debug_assert();
    }
}
