#!/usr/bin/env python
"""Diagnostic script to verify GPU setup for WhisperX/PyAnnote."""

import sys

print("=" * 60)
print("GPU DIAGNOSTIC CHECK")
print("=" * 60)

# Check PyTorch
print("\n1. PyTorch Installation:")
try:
    import torch

    print(f"   ✓ PyTorch version: {torch.__version__}")
    print(f"   ✓ PyTorch found at: {torch.__file__}")
except ImportError as e:
    print(f"   ✗ PyTorch not found: {e}")
    sys.exit(1)

# Check CUDA availability
print("\n2. CUDA Availability:")
print(f"   CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    if hasattr(torch, "version"):
        cuda_version = getattr(torch.version, "cuda", "unknown")
    else:
        cuda_version = "unknown"
    print(f"   CUDA version: {cuda_version}")
    print(f"   Number of GPUs: {torch.cuda.device_count()}")
    for i in range(torch.cuda.device_count()):
        print(f"   GPU {i}: {torch.cuda.get_device_name(i)}")
        cap = torch.cuda.get_device_capability(i)
        print(f"      Compute capability: {cap[0]}.{cap[1]}")
else:
    print("   ✗ CUDA is NOT available - GPU will not be used!")

# Check PyAnnote
print("\n3. PyAnnote Installation:")
try:
    import pyannote

    try:
        version = getattr(pyannote, "__version__", None)
    except AttributeError:
        version = None
    if version is None:
        import pyannote.audio

        version = getattr(pyannote.audio, "__version__", "unknown")
    print(f"   ✓ PyAnnote installed (version: {version})")
except ImportError as e:
    print(f"   ✗ PyAnnote not found: {e}")

# Check WhisperX
print("\n4. WhisperX Installation:")
try:
    import whisperx

    version = getattr(whisperx, "__version__", "unknown")
    print(f"   ✓ WhisperX installed (version: {version})")
except ImportError as e:
    print(f"   ✗ WhisperX not found: {e}")

# Test tensor creation on GPU
print("\n5. GPU Tensor Test:")
if torch.cuda.is_available():
    try:
        x = torch.randn(100, 100, device="cuda")
        y = torch.randn(100, 100, device="cuda")
        z = torch.matmul(x, y)
        result = z.cpu()
        print("   ✓ GPU tensor operations work")
        print(f"   ✓ Tensor created on: {z.device}")
    except Exception as e:
        print(f"   ✗ GPU tensor operations failed: {e}")
else:
    print("   ⊘ CUDA not available, skipping GPU tensor test")

print("\n" + "=" * 60)
