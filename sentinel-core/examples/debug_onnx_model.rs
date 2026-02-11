//! Debug: Print ONNX model output names

use std::path::Path;

fn main() {
    let home = std::env::var("USERPROFILE").unwrap();
    let model_path = Path::new(&home)
        .join(".sentinel")
        .join("models")
        .join("bge-m3")
        .join("model.onnx");
    
    println!("Loading ONNX model: {:?}", model_path);
    
    let session = ort::session::Session::builder()
        .expect("Session builder")
        .commit_from_file(&model_path)
        .expect("Load model");
    
    println!("\n=== ONNX Model Info ===\n");
    
    println!("Input nodes:");
    for (i, input) in session.inputs().iter().enumerate() {
        println!("  [{}] name: {:?}", i, input.name());
    }
    
    println!("\nOutput nodes:");
    for (i, output) in session.outputs().iter().enumerate() {
        println!("  [{}] name: {:?}", i, output.name());
    }
    
    println!("\n=== Done ===");
}
