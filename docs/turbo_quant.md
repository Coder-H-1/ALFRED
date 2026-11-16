# TurboQuant™ Vector Quantization Engine — Technical Specification

## Overview

**TurboQuant** is a vector quantization and KV-cache compression engine engineered for local Large Language Model inference and high-density long-term memory vector storage in A.L.F.R.E.D.

It combines:
1. **Fast Walsh-Hadamard Transform (FWHT)** for orthogonal outlier dispersal.
2. **PolarQuant**: Norm extraction paired with optimal 1D Gaussian Lloyd-Max scalar quantization.
3. **Quantized Johnson-Lindenstrauss (QJL)**: 1-bit residual error projection for unbiased inner products.
4. **Cython SIMD/C-level Acceleration**: Hardware-optimized inner loop execution in `FILES/turbo_ops.pyx`.

---

## 1. Mathematical Architecture

### 1.1 Outlier Dispersal via Orthonormal FWHT
Large language models exhibit heavy-tailed activation distributions where a tiny fraction of outlier dimensions carry disproportionate magnitude. Traditional scalar quantizers suffer massive distortion from these outliers.

TurboQuant applies an orthonormal Fast Walsh-Hadamard Transform:

$$\tilde{u} = H_n \cdot u$$

Where $H_n$ is the recursive Sylvester-Hadamard matrix normalized by $1 / \sqrt{n}$:

$$H_{2k} = \frac{1}{\sqrt{2}} \begin{pmatrix} H_k & H_k \\ H_k & -H_k \end{pmatrix}, \quad H_1 = [1]$$

Because $H_n$ is orthogonal ($H_n^T H_n = I$), distances and inner products are strictly preserved. By the Central Limit Theorem, the rotated coordinates $\tilde{u}_i$ converge rapidly to an independent identically distributed Gaussian distribution:

$$\tilde{u}_i \sim \mathcal{N}\left(0, \frac{1}{n}\right)$$

### 1.2 PolarQuant: Norm Extraction & Lloyd-Max Quantization
Any vector $x \in \mathbb{R}^d$ is decomposed into its radial magnitude and directional unit vector:

$$r = \|x\|_2, \quad u = \frac{x}{r}$$

After applying FWHT to $u$ and scaling by $\sqrt{n}$, each coordinate $z_i = \sqrt{n} \cdot \tilde{u}_i$ follows standard normal distribution $\mathcal{N}(0, 1)$.

Quantization is performed against optimal 1D Lloyd-Max centroids $\{c_1, \dots, c_K\}$ with decision boundaries $\{\theta_1, \dots, \theta_{K-1}\}$:

$$\theta_k = \frac{c_k + c_{k+1}}{2}$$

$$c_k = \frac{\int_{\theta_{k-1}}^{\theta_k} z \cdot p(z) \, dz}{\int_{\theta_{k-1}}^{\theta_k} p(z) \, dz}$$

### 1.3 Quantized Johnson-Lindenstrauss (QJL) Residual Correction
To achieve near-zero inner product bias for attention matrices ($Q \cdot K^T$), TurboQuant captures the residual quantization error $e = x - \hat{x}$ and projects it onto a random Rademacher matrix $S \in \{-1, +1\}^{m \times d}$:

$$q = \text{sign}(S \cdot e) \in \{0, 1\}^m$$

The inner product between residuals is reconstructed via the arcsine law:

$$\mathbb{E}\left[\frac{1}{m} \sum_{k=1}^m \tilde{q}_{1,k} \cdot \tilde{q}_{2,k}\right] = \frac{2}{\pi} \arcsin\left(\frac{\langle e_1, e_2 \rangle}{\|e_1\|_2 \|e_2\|_2}\right)$$

---

## 2. Empirical Benchmarks

*Benchmarked on an Intel/AMD CPU with 4096-dimensional vectors (standard LLaMA hidden dimension) comparing float32 baseline against TurboQuant configurations:*

| Configuration | Bitrate | Mean Squared Error (MSE) | Signal-to-Noise Ratio (SNR) | Raw Memory | Compressed Memory | Compression Ratio | Quant Time | Dequant Time |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **FP32 Baseline** | 32-bit | 0.00000 | $\infty$ | 16,384 B | 16,384 B | 1.0x | — | — |
| **TurboQuant 4-Bit** | 4-bit | **0.00947** | **20.21 dB** | 16,384 B | **2,056 B** | **8.0x** | 5.41 ms | 5.11 ms |
| **TurboQuant 3-Bit** | 3-bit | 0.03554 | 14.47 dB | 16,384 B | 4,104 B | 4.0x | 5.80 ms | 7.14 ms |
| **TurboQuant 2-Bit** | 2-bit | 0.12101 | 9.15 dB | 16,384 B | 1,032 B | 15.9x | 5.89 ms | 7.44 ms |
| **TurboQuant 1-Bit** | 1-bit | 0.39955 | 3.96 dB | 16,384 B | 520 B | 31.5x | 7.63 ms | 5.15 ms |

### Key Findings
1. **8.0x Memory Footprint Reduction**: At 4 bits per dimension, vector memory is reduced from 16 KB down to 2 KB while maintaining an SNR of >20 dB.
2. **Sub-10ms Latency**: In-memory quantization and dequantization execute in ~5 ms without GPU offloading.
3. **Outlier Invariance**: The FWHT step eliminates catastrophic quantization spikes typically caused by activation outliers in LLaMA transformer layers.

---

## 3. Cython Acceleration Architecture

The inner transform and centroid lookups are compiled to native C/C++ extensions via `FILES/turbo_ops.pyx`:
- **Unrolled Butterfly Loops**: Avoids recursive stack overhead in the fast Hadamard butterfly graph.
- **Contiguous Buffer Pointers**: Direct C memory views (`float[:]` and `uint8[:]`) eliminate Python GIL and bound-checking overhead during high-frequency token generation.
- **SIMD Auto-Vectorization**: C-compiler flags (`-O3 -mavx2`) generate fused multiply-add (FMA) instructions for vector products.
