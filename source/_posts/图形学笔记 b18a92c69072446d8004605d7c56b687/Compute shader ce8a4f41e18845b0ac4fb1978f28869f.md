---
title: Compute shader
date: 2022-04-07 12:00
tags: 图形学笔记
category: 笔记
---
# Compute shader

![threadgroupids.png](Compute%20shader%20ce8a4f41e18845b0ac4fb1978f28869f/threadgroupids.png)

View的话有以下几种：

ID3D11ConstantBufferView（CBV），表示Resource是只读的Buffer。

ID3D11ShaderResourceView（SRV），表示Resource是只读的Texture。
[Compute shader ce8a4f41e18845b0ac4fb1978f28869f.md](Compute%20shader%20ce8a4f41e18845b0ac4fb1978f28869f.md)
ID3D11RenderTargetView（RTV），表示Resource是只写的RenderTarget。

ID3D11DepthStencilView（DSV），表示Resource是只写的DepthStencil。

ID3D11UnorderedAccessView（UAV），表示Resource可以随机读写。

```cpp
//创建
**FRDGBufferRef** ObjectIndexBuffer = GraphBuilder.CreateBuffer(**FRDGBufferDesc**::*CreateStructuredDesc*(sizeof(**uint32**), MaxSDFMeshObjects), TEXT("ObjectIndices"));
//创建UAV，并且写入数据
PassParameters->RWObjectIndexBuffer = GraphBuilder.CreateUAV(ObjectIndexBuffer, PF_R32_UINT);
//创建SRV，别人读取他的数据
PassParameters->ObjectIndexBuffer = GraphBuilder.CreateSRV(ObjectIndexBuffer, PF_R32_UINT);
```

# ****Group Shared(群组共享)****

HLSL 使计算着色器的线程能够通过共享内存交换值。HLSL 提供了诸如**[GroupMemoryBarrierWithGroupSync](https://docs.microsoft.com/en-us/windows/win32/direct3dhlsl/groupmemorybarrierwithgroupsync)**等屏障原语，以确保在着色器中对共享内存进行正确的读取和写入顺序，并避免数据竞争。

# **extern**

将全局变量标记为着色器的外部输入;这是所有全局变量的默认标记。 不能与 **static**
组合。

# **nointerpolation**

在将顶点着色器的输出传递给像素着色器之前，不要对它们进行插值。

# **precise**

# **static**

标记一个局部变量，以便它被初始化一次并在函数调用之间保持不变。如果声明不包含初始值设定项，则该值设置为零。标记为**静态**的全局变量对应用程序不可见。

# Uniform

标记一个变量，其数据在整个着色器的执行过程中保持不变（例如顶点着色器中的材质颜色）；默认情况下，全局变量被认为是**统一的。**

# **volatile**

标记一个经常变化的变量；这是对编译器的提示。此存储类修饰符仅适用于局部变量。

[!Note]

HLSL 编译器当前忽略此存储类修饰符。

# branch

添加了branch标签的if语句shader会根据判断语句只执行当前情况的代码，这样会产生跳转指令。

# flatten

添加了flatten标签的if语句shader会执行全部情况的分支代码，然后根据判断语句来决定使用哪个结果

# unroll

添加了unroll标签的for循环是可以展开的，直到循环条件终止，代价是产生更多机器码,意思是每一次循环都写成新一行代码

![Untitled](Compute%20shader%20ce8a4f41e18845b0ac4fb1978f28869f/Untitled.png)

至于“为什么”，循环有一些开销，所以展开的情况通常更快。但占用内存更多,听说这样在for读texture会安全点

# loop

**指定[loop]时，循环在编译后的汇编代码中描述，内存大小被抑制，但执行速度稍慢。**

[SSGi](Compute%20shader%20ce8a4f41e18845b0ac4fb1978f28869f/SSGi%20a665a92db8ef49a7b8a319f527af4816.md)

[****Ambient Cube**** ](Compute%20shader%20ce8a4f41e18845b0ac4fb1978f28869f/Ambient%20Cube%20074e81bf559f43b48fa72e7c2635eae7.md)

[GTAO](Compute%20shader%20ce8a4f41e18845b0ac4fb1978f28869f/GTAO%20cdb7d5c086e44d4ca1489b7b64c373a0.md)