---
title: ShadowMap
date: 2023-1-09 19:24
count: true
tags:
- 图形学笔记
- 渲染
category: 图形学笔记
math: true
---
# ShadowMap

若用d记作物体在Shadowmap中采样获取的深度，z表示物体的光源坐标深度，f表示阴影值，那么基础Shadowmap算法可以表示为：

$$
f(z)=H(z-d)
$$

$$
H(x)=0(x\geq0), 1(x<0)
$$

# Shadow

这里直接用scenecapture2d作为灯光捕捉的深度，传到材质里，同时也把相机的VP矩阵也一起传到材质里，做深度对比。

# PCF

用泊松采样，作为扰乱采样灯光深度图uv的noise，然后在和深度做对比，就会形成周围一圈的软阴影。

# PCSS

1. 首先要用PCF作为遮挡查询，查找这里是完全遮挡还是半遮挡还是没有遮挡，判断是不是半遮挡，就是对PCF进行周围查询，所遮挡像素是不是等于采样数
2. 要是半遮挡的话，所有遮挡的深度加起来除于被遮挡的像素得到closeDepth。
3. 然后用(CurrentDepth - closeDepth)/closeDepth 得到HalfShadowSize
4. 最后用PCF在采样深度时*HalfShadowSize

# ESM

原始

1. 在深度贴图中保存 $e^{cd}$
2. 在采样阴影时计算 $e^{cz}$
3. $f(z)=e^{c(z-d)}=e^{cz-cd}=e^{-cd}*e^{cz}$
4. $f(z)=saturate(f(z))$

c值比较小的时候，ESM的漏光问题非常严重，即使c值比较大的时候依然会有一点漏光。但是若C值设得太大，软阴影的效果就不明显了，而且可能会**超过浮点数的表示上限**。如果用在移动平台上，使用16位浮点数纹理，就更容易溢出了。对32F来说，c到88就已经到极限了。但为了要让那个近似更接近原始值，c应该越大越好，否则在z-d越接近0的时候，误差会越来越大。另一个缺点在于，原始ESM要求depth在非线性的projection space，这就给点光源的阴影造成了麻烦。如果用CSM的话，projection space也会因为在不同的层级而需要分别计算，分界线可能出现跳变。

## 改进ESM

如果depth是在线性的view space，那么点光源和CSM都能用上ESM，也就是各种光源的shadow都可以切换到ESM。这个公式来自于EGSR2013上浙大的文章“Exponential Soft Shadow Mapping”。

$$
e^{-c\left(\frac{d_l-z_n}{z_f-z_n}-\frac{z_l-z_n}{z_f-z_n}\right)} = e^{-\frac{c}{z_f-z_n}(d_l-z_n)}
$$

在SIGGRAPH 2009的Advances in Real-Time Rendering in 3D Graphics and Games里，Lighting Research at Bungie就提到了logarithmic space filtering的方法。这里正是利用d-z远小于d或z的原理，把取值范围缩小了，精度也因此提高。filtering本身就是完成这个：

$$
\sum_{i=0}^N w_i e^{cd_i}
$$

其中 w 来自于gaussian filter的 kernel 。如果进一步推这个公式，就能得到：

$$
\sum_{i=0}^N w_ie^{cd_i} =e^{cd_0}\sum_{i=0}^N w_ie^{c(d_i- d_0)} =e^{cd_0}e^{\ln\left(w_0+\sum_{i=1}^N w_ie^{c(d_i-d_0)}\right)}
$$

这个被称为log space filtering。最终filter的结果是个不会溢出的量

$$
cd_0 + \ln\left(w_0+\sum_{i=1}^N w_ie^{c(d_i-d_0)}\right)
$$

1. 在Shadowmap中保存 d
2. blur中使用 $cd_0 + \ln\left(w_0+\sum_{i=1}^N w_ie^{c(d_i-d_0)}\right)$
3. 在采样阴影时计算 $e^{occluder}$
4. $f(z)=e^{c * z - occluder}$
5. $f(z)=saturate(f(z))$

代码

```hlsl ue4 custom node
int kSize = (mSize-1)/2;
float kernel[64];
float3 FinalColor = float3(0.0f,0.0f,0.0f);

float3 d0 = pow(Texture2DSample(Tex, TexSampler, UV), 2.2);
//create the 1-D kernel
float sigma = 7.0;
float Z = 0.0;
int j = 0, i = 0;
for (j = 0; j <= kSize; j++)
{
    kernel[kSize + j] = kernel[kSize - j] = 0.39894 * exp(-0.5 * float(j) * float(j) / (sigma * sigma)) / sigma;
}

//get the normalization factor (as the gaussian has been clamped)
for (j = 0; j < kSize * 2 + 1; j++)
{
    Z += kernel[j];
}

//read out the texels
for (i=-kSize; i <= kSize; i++)
{
    for (j=-kSize; j <= kSize; j++)
    {
        float3 di = pow(Texture2DSample(Tex, TexSampler, UV + float2(1.0 * i / 512 * dist, 1.0 * j / 512 * dist)), 2.2);
        FinalColor += kernel[kSize+j] * kernel[kSize+i] * exp(c * (di - d0));
    }
}

FinalColor = log(FinalColor/(Z * Z)) + c * d0;
return float4(FinalColor, 1.0);
```