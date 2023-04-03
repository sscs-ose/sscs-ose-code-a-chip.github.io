<a target="_blank" href="https://colab.research.google.com/drive/10ER7BmSm4vbRMsVznXbMqf84Xr6Ze5Lc#scrollTo=NC__X6Jph4CU">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/>
</a>

# An Open Source E4M3 FP8 Addition Module for Accelerating Decoder-only Generative Neural Networks

Recent advancements in transformers and specialized accelerators, such as NVIDIA's H100, have revolutionized the AI landscape. The use of reduced-precision formats, like int4 and int8, significantly accelerates training and inference. However, these formats may lack the dynamic range required for NLP applications, driving the adoption of low-precision floating-point formats like FP8 [^1].

Among various FP8 formats, E4M3 stands out due to its balance between precision and dynamic range [^2], making it a superior alternative to int4 and int8 for deep learning applications, including decoder-only generative neural networks like ChatGPT. Notably, NVIDIA's H100 (Hopper) has added FP8 tensor core precision support, while dropping support for int4 and int8 formats [^3].

This open-source implementation empowers researchers and hardware developers to optimize and customize arithmetic operations, improving energy efficiency and performance. Additionally, it fosters widespread adoption of reduced-precision floating-point formats in deep learning applications, encouraging innovation and efficient resource utilization. As the demand for powerful AI solutions grows, open-source implementations like our E4M3 FP8 addition module play a vital role in democratizing AI and propelling the development of cutting-edge technologies.

## License

```
SPDX-License-Identifier: Apache-2.0
```

