//! WinDivert Device for smoltcp
//!
//! Implements smoltcp::phy::Device trait to bridge WinDivert packet capture
//! with the smoltcp user-space TCP/IP stack.

use std::collections::VecDeque;
use std::sync::{Arc, Mutex};
use smoltcp::phy::{self, Device, DeviceCapabilities, Medium};
use smoltcp::time::Instant;
use tracing::{debug, trace};

/// Maximum Transmission Unit for our virtual device
const MTU: usize = 65535;

/// Queue of packets received from WinDivert
type PacketQueue = Arc<Mutex<VecDeque<Vec<u8>>>>;

/// WinDivert-based device for smoltcp stack
pub struct WinDivertDevice {
    /// Queue for incoming packets (from WinDivert)
    rx_queue: PacketQueue,
    /// Queue for outgoing packets (to WinDivert for reinject)
    tx_queue: PacketQueue,
}

impl WinDivertDevice {
    /// Create a new WinDivert device with packet queues
    pub fn new(rx_queue: PacketQueue, tx_queue: PacketQueue) -> Self {
        Self { rx_queue, tx_queue }
    }
    
    /// Create a device with new internal queues
    /// Returns (device, rx_feeder, tx_collector)
    pub fn create() -> (Self, PacketQueue, PacketQueue) {
        let rx_queue: PacketQueue = Arc::new(Mutex::new(VecDeque::with_capacity(1024)));
        let tx_queue: PacketQueue = Arc::new(Mutex::new(VecDeque::with_capacity(1024)));
        
        let device = Self {
            rx_queue: Arc::clone(&rx_queue),
            tx_queue: Arc::clone(&tx_queue),
        };
        
        (device, rx_queue, tx_queue)
    }
    
    /// Feed a packet received from WinDivert into the device
    pub fn feed_packet(rx_queue: &PacketQueue, packet: Vec<u8>) {
        let mut queue = rx_queue.lock().unwrap();
        if queue.len() < 4096 {
            queue.push_back(packet);
        } else {
            debug!("Dropping packet, queue full");
        }
    }
    
    /// Collect a packet from the device for WinDivert reinject
    pub fn collect_packet(tx_queue: &PacketQueue) -> Option<Vec<u8>> {
        let mut queue = tx_queue.lock().unwrap();
        queue.pop_front()
    }
}

/// Receive token for smoltcp
pub struct WinDivertRxToken {
    buffer: Vec<u8>,
}

impl phy::RxToken for WinDivertRxToken {
    fn consume<R, F>(self, f: F) -> R
    where
        F: FnOnce(&[u8]) -> R,
    {
        f(&self.buffer)
    }
}

/// Transmit token for smoltcp
pub struct WinDivertTxToken {
    tx_queue: PacketQueue,
}

impl phy::TxToken for WinDivertTxToken {
    fn consume<R, F>(self, len: usize, f: F) -> R
    where
        F: FnOnce(&mut [u8]) -> R,
    {
        let mut buffer = vec![0u8; len];
        let result = f(&mut buffer);
        
        // Queue packet for WinDivert reinject
        let mut queue = self.tx_queue.lock().unwrap();
        if queue.len() < 4096 {
            queue.push_back(buffer);
        }
        
        result
    }
}

impl Device for WinDivertDevice {
    type RxToken<'a> = WinDivertRxToken where Self: 'a;
    type TxToken<'a> = WinDivertTxToken where Self: 'a;

    fn receive(&mut self, _timestamp: Instant) -> Option<(Self::RxToken<'_>, Self::TxToken<'_>)> {
        let mut rx_queue = self.rx_queue.lock().unwrap();
        
        if let Some(buffer) = rx_queue.pop_front() {
            trace!("smoltcp receive: {} bytes", buffer.len());
            
            let rx_token = WinDivertRxToken { buffer };
            let tx_token = WinDivertTxToken {
                tx_queue: Arc::clone(&self.tx_queue),
            };
            
            Some((rx_token, tx_token))
        } else {
            None
        }
    }

    fn transmit(&mut self, _timestamp: Instant) -> Option<Self::TxToken<'_>> {
        Some(WinDivertTxToken {
            tx_queue: Arc::clone(&self.tx_queue),
        })
    }

    fn capabilities(&self) -> DeviceCapabilities {
        let mut caps = DeviceCapabilities::default();
        caps.medium = Medium::Ip; // We handle IP packets directly
        caps.max_transmission_unit = MTU;
        caps
    }
}
