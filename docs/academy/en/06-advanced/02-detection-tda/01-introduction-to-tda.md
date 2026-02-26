# Introduction to TDA for Attack Detection

> **Lesson:** 06.2.1 - Introduction to Topological Data Analysis  
> **Time:** 45 minutes  
> **Level:** Advanced

---

## Learning Objectives

By the end of this lesson, you will be able to:

1. Understand TDA fundamentals for security
2. Apply persistent homology to attack detection
3. Use topological features for anomaly detection
4. Integrate TDA with SENTINEL engines

---

## What is Topological Data Analysis?

TDA analyzes the "shape" of data using concepts from algebraic topology:

| Concept | Application to Security |
|---------|----------------------|
| **Connected Components** | Cluster separation in embeddings |
| **Holes/Loops** | Circular patterns in attack vectors |
| **Voids** | Missing regions in normal behavior |
| **Persistent Homology** | Robust feature extraction |

---

## Why TDA for AI Security?

Traditional ML metrics (distance, density) can be fooled. TDA captures topological invariants:

```python
# Traditional: Easily fooled by adversarial perturbations
euclidean_distance = np.linalg.norm(embedding_a - embedding_b)
# Small perturbation → similar distance → missed attack

# TDA: Captures structural properties
topological_features = compute_persistent_homology(embedding_space)
# Structural anomaly unchanged by small perturbations
```

---

## Persistent Homology Basics

### Simplicial Complexes

Build structure from point cloud:

```python
import numpy as np
from ripser import ripser
from persim import plot_diagrams

def demonstrate_simplicial_complex(points: np.ndarray, epsilon: float):
    """
    Build Vietoris-Rips complex from points.
    
    1. Start with points (0-simplices)
    2. Connect points within ε (1-simplices/edges)
    3. Fill triangles if all edges exist (2-simplices)
    4. Continue for higher dimensions
    """
    from scipy.spatial.distance import pdist, squareform
    
    distances = squareform(pdist(points))
    
    # 0-simplices: all points
    simplices_0 = list(range(len(points)))
    
    # 1-simplices: edges where distance < epsilon
    simplices_1 = []
    for i in range(len(points)):
        for j in range(i+1, len(points)):
            if distances[i, j] < epsilon:
                simplices_1.append((i, j))
    
    # 2-simplices: triangles where all three edges exist
    simplices_2 = []
    edges_set = set(simplices_1)
    for i in range(len(points)):
        for j in range(i+1, len(points)):
            for k in range(j+1, len(points)):
                if ((i,j) in edges_set and 
                    (j,k) in edges_set and 
                    (i,k) in edges_set):
                    simplices_2.append((i, j, k))
    
    return {
        0: simplices_0,
        1: simplices_1,
        2: simplices_2
    }
```

### Persistence Diagrams

```python
def compute_persistence_diagram(embeddings: np.ndarray) -> dict:
    """
    Compute persistent homology and return diagram.
    
    Each point (birth, death) represents a topological feature:
    - birth: scale at which feature appears
    - death: scale at which feature disappears
    - persistence = death - birth (feature significance)
    """
    from ripser import ripser
    
    # Compute persistent homology up to dimension 2
    result = ripser(embeddings, maxdim=2)
    
    return {
        "H0": result["dgms"][0],  # Connected components
        "H1": result["dgms"][1],  # Loops/holes
        "H2": result["dgms"][2] if len(result["dgms"]) > 2 else [],  # Voids
    }

def extract_topological_features(diagram: dict) -> dict:
    """Extract features from persistence diagram."""
    features = {}
    
    for dim, dgm in diagram.items():
        if len(dgm) == 0:
            features[f"{dim}_count"] = 0
            features[f"{dim}_max_persistence"] = 0
            features[f"{dim}_mean_persistence"] = 0
            continue
        
        # Filter infinite points
        finite_dgm = dgm[dgm[:, 1] != np.inf]
        
        if len(finite_dgm) == 0:
            features[f"{dim}_count"] = 0
            features[f"{dim}_max_persistence"] = 0
            features[f"{dim}_mean_persistence"] = 0
            continue
        
        persistence = finite_dgm[:, 1] - finite_dgm[:, 0]
        
        features[f"{dim}_count"] = len(finite_dgm)
        features[f"{dim}_max_persistence"] = np.max(persistence)
        features[f"{dim}_mean_persistence"] = np.mean(persistence)
        features[f"{dim}_total_persistence"] = np.sum(persistence)
        features[f"{dim}_std_persistence"] = np.std(persistence)
    
    return features
```

---

## TDA for Attack Detection

### 1. Embedding Space Topology

```python
class TopologicalAnomalyDetector:
    """Detect anomalies using topological features."""
    
    def __init__(self, embedding_model):
        self.embed = embedding_model
        self.baseline_topology = None
    
    def fit(self, normal_samples: list):
        """Learn baseline topology from normal samples."""
        
        # Embed samples
        embeddings = np.array([self.embed(s) for s in normal_samples])
        
        # Compute persistent homology
        diagram = compute_persistence_diagram(embeddings)
        
        # Store baseline features
        self.baseline_topology = extract_topological_features(diagram)
        
        # Also store for comparison
        self.baseline_embeddings = embeddings
        self.baseline_diagram = diagram
    
    def detect(self, sample: str) -> dict:
        """Detect if sample is topologically anomalous."""
        
        # Embed sample
        sample_emb = self.embed(sample).reshape(1, -1)
        
        # Combine with baseline to see effect
        combined = np.vstack([self.baseline_embeddings, sample_emb])
        
        # Compute new topology
        new_diagram = compute_persistence_diagram(combined)
        new_features = extract_topological_features(new_diagram)
        
        # Compare to baseline
        anomaly_score = self._compute_topological_distance(
            self.baseline_topology, 
            new_features
        )
        
        return {
            "is_anomaly": anomaly_score > self.threshold,
            "score": anomaly_score,
            "baseline_features": self.baseline_topology,
            "sample_features": new_features,
        }
    
    def _compute_topological_distance(self, f1: dict, f2: dict) -> float:
        """Compute distance between topological feature sets."""
        
        distance = 0
        for key in f1.keys():
            if key in f2:
                distance += abs(f1[key] - f2[key])
        
        return distance / len(f1)
```

---

### 2. Conversation Trajectory Analysis

```python
class ConversationTopologyAnalyzer:
    """Analyze conversation trajectories using TDA."""
    
    def __init__(self, embedding_model):
        self.embed = embedding_model
    
    def analyze_conversation(self, turns: list) -> dict:
        """Analyze topological properties of conversation trajectory."""
        
        # Embed each turn
        embeddings = np.array([self.embed(t["content"]) for t in turns])
        
        # Compute persistence
        diagram = compute_persistence_diagram(embeddings)
        features = extract_topological_features(diagram)
        
        # Specific conversation metrics
        trajectory_metrics = self._compute_trajectory_metrics(embeddings)
        
        # Detect suspicious patterns
        suspicious_patterns = self._detect_suspicious_topology(diagram)
        
        return {
            "topological_features": features,
            "trajectory_metrics": trajectory_metrics,
            "suspicious_patterns": suspicious_patterns,
            "is_suspicious": len(suspicious_patterns) > 0
        }
    
    def _compute_trajectory_metrics(self, embeddings: np.ndarray) -> dict:
        """Compute trajectory-specific metrics."""
        
        # Compute pairwise distances
        from scipy.spatial.distance import pdist, squareform
        distances = squareform(pdist(embeddings))
        
        # Consecutive turn distances
        consecutive = [distances[i, i+1] for i in range(len(embeddings)-1)]
        
        # Check for "looping" behavior (getting close to earlier turns)
        loops = []
        for i in range(len(embeddings)):
            for j in range(i+2, len(embeddings)):  # Skip adjacent
                if distances[i, j] < 0.3 * np.mean(consecutive):
                    loops.append((i, j, distances[i, j]))
        
        return {
            "avg_step_distance": np.mean(consecutive),
            "max_step_distance": np.max(consecutive),
            "step_variance": np.var(consecutive),
            "loops_detected": len(loops),
            "loop_details": loops
        }
    
    def _detect_suspicious_topology(self, diagram: dict) -> list:
        """Detect suspicious topological patterns."""
        patterns = []
        
        # Many H1 features = circular/looping conversation
        h1_count = len([p for p in diagram["H1"] if p[1] != np.inf])
        if h1_count >= 3:
            patterns.append({
                "type": "circular_conversation",
                "evidence": f"{h1_count} loops detected"
            })
        
        # High persistence in H1 = significant loops
        if len(diagram["H1"]) > 0:
            max_h1_persistence = max(
                p[1] - p[0] for p in diagram["H1"] if p[1] != np.inf
            ) if any(p[1] != np.inf for p in diagram["H1"]) else 0
            
            if max_h1_persistence > 0.5:
                patterns.append({
                    "type": "significant_loop",
                    "persistence": max_h1_persistence
                })
        
        return patterns
```

---

### 3. Prompt Cluster Analysis

```python
class PromptClusterAnalyzer:
    """Use TDA to analyze prompt clusters for attack patterns."""
    
    def __init__(self, embedding_model, attack_examples: list, benign_examples: list):
        self.embed = embedding_model
        
        # Embed known examples
        self.attack_embeddings = np.array([self.embed(p) for p in attack_examples])
        self.benign_embeddings = np.array([self.embed(p) for p in benign_examples])
        
        # Compute baseline topologies
        self.attack_topology = compute_persistence_diagram(self.attack_embeddings)
        self.benign_topology = compute_persistence_diagram(self.benign_embeddings)
    
    def classify_prompt(self, prompt: str) -> dict:
        """Classify prompt based on topological similarity."""
        
        prompt_emb = self.embed(prompt)
        
        # Add to each cluster and compute topology change
        with_attack = np.vstack([self.attack_embeddings, prompt_emb])
        with_benign = np.vstack([self.benign_embeddings, prompt_emb])
        
        attack_with_prompt = compute_persistence_diagram(with_attack)
        benign_with_prompt = compute_persistence_diagram(with_benign)
        
        # Measure topological disruption
        attack_disruption = self._compute_disruption(
            self.attack_topology, attack_with_prompt
        )
        benign_disruption = self._compute_disruption(
            self.benign_topology, benign_with_prompt
        )
        
        # Lower disruption = better fit
        is_attack = attack_disruption < benign_disruption
        
        return {
            "classification": "attack" if is_attack else "benign",
            "attack_fit": 1 - attack_disruption,
            "benign_fit": 1 - benign_disruption,
            "confidence": abs(attack_disruption - benign_disruption)
        }
    
    def _compute_disruption(self, original: dict, with_new: dict) -> float:
        """Compute how much adding new point disrupts topology."""
        from persim import wasserstein
        
        total_disruption = 0
        for dim in ["H0", "H1"]:
            if dim in original and dim in with_new:
                total_disruption += wasserstein(
                    original[dim], with_new[dim]
                )
        
        return total_disruption
```

---

## SENTINEL Integration

```python
from sentinel import TDAEngine, configure

configure(
    tda_detection=True,
    persistence_threshold=0.3,
    dimension=2
)

tda_engine = TDAEngine(
    embedding_model="all-MiniLM-L6-v2",
    baseline_samples=normal_prompts
)

result = tda_engine.analyze(prompt)

if result.topological_anomaly:
    log_alert("Topological anomaly detected", result.features)
```

---

## Key Takeaways

1. **TDA captures shape** - Robust to perturbations
2. **Persistence matters** - Long-lived features are significant
3. **Loops indicate patterns** - Circular conversations are suspicious
4. **Combine with ML** - TDA features enhance classifiers
5. **SENTINEL integration** - Built-in TDA engine support

---

*AI Security Academy | Lesson 06.2.1*
