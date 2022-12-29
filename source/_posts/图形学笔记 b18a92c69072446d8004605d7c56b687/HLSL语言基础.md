---
title: HLSL语言基础
date: 2022-04-07 12:00
count: true
tags: 图形学笔记
category: 图形学笔记
---
# HLSL语言基础

[HLSL](https://en.wikipedia.org/wiki/High-Level_Shading_Language)(High-Level Shading Language， [高级着色语言](https://zh.wikipedia.org/wiki/%E9%AB%98%E7%BA%A7%E7%9D%80%E8%89%B2%E5%99%A8%E8%AF%AD%E8%A8%80)) 是由微软开发的一种着色器语言，D3D9及以上版本使用其作为着色语言（注：D3D8的shader使用是类似于汇编的语言来编写），拥有如下特点：

1. 基于C语言的语法（如：大小写敏感，每条语句必须以分号结尾），是一门面向过程的强类型语言（type sensitive language）
2. 除了bool、int、uint、half、float、double基础类型外，还支持数组类型，另外HLSL还内置了适合3D图形操作的向量与矩阵类型，以及采样器（纹理）类型
3. 基础类型的隐式转换规则与C语言一致
4. 变量没有赋初值时，都会被填充为false、0或0.0
5. if条件语句和switch条件语句与C语言一致
6. for循环语句和while循环语句与C语言一致
7. return、continue和break与C语言一致。另外引入了discard，该关键字只能在ps中使用，表示放弃当前像素，直接处理下一个像素。
8. 无指针、无字符和字符串类型
9. 无union、无enum
10. 向量、矩阵可通过构造函数进行初始化

# **通用着色器的核心**

所有的可编程着色器阶段使用通用着色器核心来实现相同的基础功能。此外，顶点着色阶段、几何着色阶段和像素着色阶段则提供了独特的功能。

例如几何着色阶段可以生成新的图元或删减图元，像素着色阶段可以决定当前像素是否被抛弃等。

下图展示了数据是怎么流向一个着色阶段，以及通用着色器核心与着色器内存资源之间的关系：

**Input Data**：顶点着色器从输入装配阶段获取数据；几何着色器则从上一个着色阶段的输出获取等等。通过给形参引入可以使用的系统值可以提供额外的输入

**Output Data**：着色器生成输出的结果然后传递给管线的下一个阶段。有些输出会被通用着色器核心解释成特定用途（如顶点位置、渲染目标对应位置的值），另外一些输出则由应用程序来解释。

**Shader Code**：着色器代码可以从内存读取，然后用于执行代码中所期望的内容。

**Samplers**：采样器决定了如何对纹理进行采样和滤波。

**Textures**：纹理可以使用采样器进行采样，也可以基于索引的方式按像素读取。

**Buffers**：缓冲区可以使用读取相关的内置函数，在内存中按元素直接读取。

**Constant Buffers**：常量缓冲区对常量值的读取有所优化。他们被设计用于CPU对这些数据的频繁更新，因此他们有额外的大小、布局和访问限制。

## **注释**

单行注释

多行注释

```raw raw
/*********************************
 This is my first HLSL.
 Let's take a look.
*********************************/
```

## **预处理**

#if #elif [defined(), !defined()] #else #ifdef #ifndef #endif // 条件编译

```hlsl hlsl
#define TEST1  // 定义为空的宏

#ifdef TEST1  // 条件成立
#endif

#define TEST1 1 // 定义TEST1宏为1  注：可以不用先undef TEST1宏 但会报warning X1519: 'TEST1' : macro redefinition

#undef TEST1  // 取消TEST1宏

#if TEST1  // 条件不成立
#endif

#ifndef TEST1  // 条件成立
#endif

#define TEST1 -1  // 定义为int的宏

#define TEST2 // 定义为空的宏

#if TEST1 && defined(TEST2) // 条件成立
#endif

#define TEST3 true // 定义为bool的宏

#if TEST3  // 条件不成立
#endif

#if !TEST3  // 条件成立
#endif

#if TEST3==true  // 条件成立
#endif

#if !defined(TEST0) && TEST1 && defined(TEST2) // 条件成立
#endif

#define TEST4 100  // 定义为int的宏

#if TEST4  // 条件成立
#endif

#if TEST4 > 150
#elif (TEST4 > 120) || TEST1 // 进入elif分支
#endif

#if TEST4 > 160
#else // 进入else分支
#define XX2 1
#endif

#if !TEST4
#elif (TEST4 > 110)
#else // 进入else分支
#endif

#define TEST5 2.0  // 定义为float的宏

//#if TEST5  //float不能进行条件判断  编译失败
//#endif

//#if TEST5>0.0  //float不能进行条件判断  编译失败
//#endif1.2.3.4.5.6.7.8.9.10.11.12.13.14.15.16.17.18.19.20.21.22.23.24.25.26.27.28.29.30.31.32.33.34.35.36.37.38.39.40.41.42.43.44.45.46.47.48.49.50.51.52.53.54.55.56.57.58.59.60.61.62.
```

#define #undef // 宏定义、宏取消

```raw raw
#define TEST1 100  // 定义TEST1宏为100

#ifdef TEST1  // 条件成立
#undef TEST1   // 取消TEST1宏的定义
#endif

#if !defined(TEST1) // 条件成立
#endif

#define SQUARE(a) ((a)*(a))

#define MAX(a,b) \
    (((a) > (b)) ? (a) : (b)) // 宏必须在一行写完，多行写时必须带上 \行连接符，但要注意\后不要有空格，否则会编译失败

#define MERGE(a, b) a##b // ## 字符拼接符1.2.3.4.5.6.7.8.9.10.11.12.13.14.15.
```

#line // 指示下一行的行号，及当前所在的文件；该命令会修改__FILE__、__LINE__的值

该命令是提供给编译器使用的，程序员最好不要使用该命令

```raw raw
#if __LINE__==10  // 判断当前行号是否为10
#endif

#if __FILE__==0  // 条件成立  __FILE__始终为0
#endif

#line 116 // 指定下一行的行号为116
#if __LINE__==116  // 条件成立
#endif

#line 200 "test.hlsl"  // 指定下一行的行号为200，当前文件的ID标识为5
#if __FILE__==0  // 条件成立   __FILE__始终为0
#endif

// test.hlsl(204,2): error: This is an error!
#error This is an error!1.2.3.4.5.6.7.8.9.10.11.12.13.14.15.16.
```

#error // error命令被执行，会导致当前文件编译失败

```raw raw
// E:\ModenD3D\HLSL-Development-Cookbook\book_sample\Chpater 1 - Forward Light\Ambient Light\ForwardLight.hlsl(40,2): error: This is an error!
#error This is an error!
```

#pragma // 用来控制编译器的一些行为

```raw raw
#pragma warning( disable : 1519; once : 3205; error : 3206 ) // 忽略1519 warning，只报一次3205 warning，3206 warning视为error

#define TEST1  // 定义为空的宏
#define TEST1 1 // 定义TEST1宏为1  注：可以不用先undef TEST1宏 但会报warning X1519: 'TEST1' : macro redefinition

#pragma message("Hello HLSL.") //Hello HLSL.

#pragma pack_matrix( column_major ) // 将uniform参数的matrix设置成列主序（缺省）  注1：列主序生成的指令数更少，因此其效率比行主序的效率要高  注2：构造matrix时不受#pragma pack_matrix影响，始终为行主序
#pragma pack_matrix( row_major ) // 将uniform参数的matrix设置成行主序

#error This is an error! // hlsl中出现error时，才会打印pragma message和warning信息1.2.3.4.5.6.7.8.9.10.11.
```

注1：需要注意的是，hlsl中出现error时（#error或语法错误），才会打印pragma message和warning信息

注2：更多error、warning number说明，详见： [https://docs.microsoft.com/en-us/windows/win32/direct3dhlsl/hlsl-errors-and-warnings](https://docs.microsoft.com/en-us/windows/win32/direct3dhlsl/hlsl-errors-and-warnings)

注3：在C++代码层中，DirectXMath数学库创建的矩阵都是行矩阵，但当矩阵从C++传递给HLSL时，HLSL默认是列矩阵的，因此传递前要进行了一次转置。如果希望不发生转置操作的话，可以添加修饰关键字row_major

#include // 引用其他hlsl文件 与c/c++语言用法一致

```raw raw
#include "common.hlsl" // 引用其他的hlsl文件
```

**typedef**

用于类型的别名，用法与C语言一致

```raw raw
typedef vector<float, 3> POINT;
typedef const float CFLOAT;

POINT pt;
CFLOAT cf1;
```

**运算符**

除了没有指针相关的运算符外，其他的与c语言完全一致

注1：对于向量、矩阵类型，运算符会在各个分量上进行

注2：支持浮点数取模%

```raw raw
int n1 = 5 % 3;  // 取模即求余数，结果为2
float f1 = 3.3 % 1.6; // 3.3-(int)(3.3/1.6)*1.6 = 3.3-2*1.6 = 0.1
float f2 = -3.3 % 1.6; // -3.3-(int)(-3.3/1.6)*1.6 = -3.3-(-2*1.6) = -0.1
```

注3：二元运算中变量类型的提升规则：

① 对于二元运算来说，如果运算符左右操作数的维度不同，那么维度较小的变量类型将会被隐式提升为维度较大的变量类型。但是这种提升仅限于标量到向量的提升，即x会变为(x, x, x)。但是不支持像float2到float3的提升。

② 对于二元运算来说，如果运算符左右的操作数类型不同，那么低精度变量的类型将被隐式提升为高精度变量的类型，这点和C/C++是类似的。

---

## **控制流**

### **条件语句**

HLSL也支持`if`, `else`, `continue`, `break`, `switch`关键字，此外`discard`关键字用于像素着色阶段抛弃该像素。

条件的判断使用一个布尔值进行，通常由各种逻辑运算符或者比较运算符操作得到。注意向量之间的比较或者逻辑操作是得到一个存有布尔值的向量，不能够直接用于条件判断，也不能用于`switch`语句。

### 判断与动态分支

基于值的条件分支只有在程序执行的时候被编译好的着色器汇编成两种方式：**判断(predication)**和**动态分支(dynamic branching)**。

如果使用的是判断的形式，编译器会提前计算两个不同分支下表达式的值。然后使用比较指令来基于比较结果来"选择"正确的值。

而动态分支使用的是跳转指令来避免一些非必要的计算和内存访问。

着色器程序在同时执行的时候应当选择相同的分支，以防止硬件在分支的两边执行。通常情况下，硬件会同时将一系列连续的顶点数据传入到顶点着色器并行计算，或者是一系列连续的像素单元传入到像素着色器同时运算等。

动态分支会由于执行分支指令所带来的开销而导致一定的性能损失，因此要权衡动态分支的开销和可以跳过的指令数目。

通常情况下编译器会自行选择使用判断还是动态分支，但我们可以通过重写某些属性来修改编译器的行为。我们可以在条件语句前可以选择添加下面两个属性之一：

| 属性 | 描述 |
| --- | --- |
| [branch] | 缺省。根据条件值的结果，只计算其中一边的内容，会产生跳转指令。 |
| [flatten] | 两边的分支内容都会计算，然后根据条件值选择其中一边。可以避免跳转指令的产生。 |

```raw raw
[flatten]
if (x)
{
    x = sqrt(x);
}1.2.3.4.5.
```

### **循环语句**

HLSL也支持`for`, `while`和`do while`循环。和条件语句一样，它可能也会在基于运行时的条件值判断而产生动态分支，从而影响程序性能。用法如下：

| 属性 | 描述 |
| --- | --- |
| [loop] | 缺省。默认不加属性的循环语句为loop型。 |
| [unroll] | 如果循环次数较小，我们可以使用属性[unroll]来展开循环，代价是产生更多的汇编指令。 |

```raw raw
times = 4;
sum = times;
[unroll]
while (times--)
{
    sum += times;
}1.2.3.4.5.6.7.
```

### **寄存器（register）**

用于在C++与HLSL之间传递数据，包括如下4种：

| 寄存器 | 说明 | 上限 |
| --- | --- | --- |
| b | 常量缓冲区视图 (CBV)，用于从C++传递只读数据给HLSL | 15个常量缓冲区（共16个，系统内部保留1个） |
| t | 着色器资源视图 (SRV)，用于从C++传递只读内存块或纹理数据给HLSL | 128个 |
| u | 无序访问视图 (UAV)，用于可读写数据的传递 |  |
| s | 用于从C++传递采样器设置给HLSL | 128个 |

### **变量**

变量名需要符合以下规则：

① 只能包括大小写字母、数字和下划线

② 变量名不能以数字开头

③ 不能是关键字或预留的关键字

全局变量：定义在函数体外的变量。作用域规则与c语言全局变量一致。

局部变量：定义在函数内的变量。作用域规则与c语言局部变量一致。

const变量

该变量为一常量，需要被初始化，在运行时不能被修改，与c/c++用法一致

static变量

进一步可分为static局部变量和static全局变量，与c/c++用法一致

static局部变量需要在HLSL中自己初始化，否则使用默认初始化，初始化操作仅执行一次（首次被访问时）

只在着色器内部可见

extern变量

在全局变量上可用，非静态的全局变量默认是extern类型

可在着色器外被访问，比如被C++应用程序

uniform变量

在D3D代码中初始化，然后再作为输入传给着色器

允许在C++应用层中修改，但在着色器执行的过程中，其值始终保持不变（运行前可变，运行时不变）。着色器程序中的全局变量默认为既uniform又extern

volatile变量

表示该变量经常被修改，用于局部变量

shared变量

在全局变量上可用，提示效果框架该变量可在多个效果之间共享

nointerpolation -- 修饰的变量，在将顶点着色器的输出传递到像素着色器之前，请勿对其进行插值

groupshared -- 将一个变量标记为用于计算着色器的线程组共享内存

precise -- 用于保证该变量在计算时，是严格精确的

row_major -- 标记一个可在单个行中存储4个成分的变量，以便可以将它们存储在单个常量寄存器中

column_major -- 标记一个可在单个列中存储4个成分的变量，以优化矩阵数学 （缺省）

### **语义**

[语义](https://docs.microsoft.com/en-us/windows/win32/direct3dhlsl/dx-graphics-hlsl-semantics)通常是附加在着色器输入/输出参数上的字符串。它在着色器程序的用途如下：

1. 用于描述传递给着色器程序的变量参数的含义
2. 允许着色器程序接受由渲染管线生成的特殊系统值
3. 允许着色器程序传递由渲染管线解释的特殊系统值

## vs语义

| 语义 | 描述 | 是否可作为输入关联 | 是否可作为输出关联 | 类型 |
| --- | --- | --- | --- | --- |
| BINORMAL[n] | 副法线（副切线）向量 | Yes |  | float4 |
| BLENDINDICES[n] | 混合索引 | Yes |  | uint |
| BLENDWEIGHT[n] | 混合权重 | Yes |  | float |
| COLOR[n] | 漫反射/镜面反射颜色 | Yes | Yes | float4 |
| NORMAL[n] | 法向量 | Yes |  | float4 |
| POSITION[n] | 物体坐标系下的顶点坐标 | Yes | Yes | float4 |
| PSIZE[n] | 点的大小 | Yes | Yes | float |
| TANGENT[n] | 切线向量 | Yes |  | float4 |
| TEXCOORD[n] | 纹理坐标 | Yes | Yes | float4 |
| FOG | 顶点雾 |  | Yes | float |

注1：n是一个可选的整数，从0开始。比如POSITION0, TEXCOORD1等等。

注2：vs的输出关联将其运算得到的结果经过光栅化插值后链接到ps的输入关联上.

## **ps语义**

| 语义 | 描述 | 是否可作为输入关联 | 是否可作为输出关联 | 类型 |
| --- | --- | --- | --- | --- |
| COLOR[n] | 漫反射/镜面反射颜色 | Yes | Yes | float4 |
| TEXCOORD[n] | 纹理坐标 | Yes |  | float4 |
| VFACE | 负数表示为背面 
正数表示为正面 | Yes |  | float |
| VPOS | 像素所在坐标 | Yes |  | float2 |
| DEPTH[n] | 深度值 |  | Yes | float |

注： ps输出关联将其输出颜色绑定给正确的RT上（渲染目标）。其中颜色输出被连接到alpha混合阶段，DEPTH输出关联用于改变当前光栅化位置的目标深度值

## **系统值语义**

所有的系统值都包含前缀`SV_`，后面的部分大小写不敏感，例如：SV_Positon和SV_POSITION是一样的。这些系统值将用于某些着色器的特定用途。

| 系统值 | 描述 | 类型 |
| --- | --- | --- |
| SV_Depth | 深度缓冲区数据，可以被任何着色器写入/读取 | float |
| SV_InstanceID | 每个实例都会在运行期间自动生成一个ID。在任何着色器阶段都能读取 | uint |
| SV_IsFrontFace | 指定该三角形是否为正面。可以被几何着色器写入，以及可以被像素着色器读取 | bool |
| SV_Position | 若被声明用于输入到着色器，它描述的是像素位置，在所有着色器中都可用，可能会有0.5的偏移值 | float4 |
| SV_PrimitiveID | 每个原始拓扑都会在运行期间自动生成一个ID。可用在几何/像素着色器中写入，也可以在像素/几何/外壳/域着色器中读取 | uint |
| SV_StencilRef | 代表当前像素着色器的模板引用值。只可以被像素着色器写入 | uint |
| SV_VertexID | 每个实例都会在运行期间自动生成一个ID。仅允许作为顶点着色器的输入 | uint |
| SV_TARGET | SV_TARGET即Color缓存区（帧缓存，FrameBuffer） |  |
| SV_TARGET[n] 0 <= n <= 7 | MRT有多个RenderTarget输出 |  |
| SV_ClipDistance0 |  |  |
| SV_RenderTargetArrayIndex |  |  |
| SV_TessFactor |  |  |
| SV_InsideTessFactor |  |  |
| SV_DomainLocation |  |  |
| SV_GroupID |  |  |
| SV_GroupIndex |  |  |
| SV_GroupThreadID |  |  |
| SV_DispatchThreadID |  |  |

### **着色器常量**

[着色器常量](https://docs.microsoft.com/en-us/windows/win32/direct3dhlsl/dx-graphics-hlsl-constants)存在内存中的一个或多个缓冲区资源当中。他们可以被组织成两种类型的缓冲区：常量缓冲区（cbuffers）和纹理缓冲区（tbuffers）。

## **常量缓冲区(Constant Buffer)**

常量缓冲区允许C++端将数据传递给HLSL中使用，在HLSL中，这些传递过来的数据不可更改，因而是常量。常量缓冲区对这种使用方式有所优化，表现为低延迟的访问和允许来自CPU的频繁更新，因此他们有额外的大小、布局和访问限制。

① 每个着色器阶段最多允许15个常量缓冲区（共16个，系统内部保留1个），并且每个缓冲区最多可以容纳4096个标量（每个vector最多包含4个float类型）。HLSL的cbuffer需要指定register(b#), #的范围为0到14

② 在C++创建常量缓冲区时大小必须为16字节的倍数，因为HLSL的常量缓冲区本身以及对它的读写操作需要严格按16字节对齐

③ 对常量缓冲区的成员使用packoffset修饰符可以指定起始向量和分量位置

④ 在更新常量缓冲区时由于数据是提交完整的字节流数据到GPU，会导致HLSL中cbuffer的所有成员都被更新。为了减少不必要的更新，可以根据这些参数的更新频率划分出多个常量缓冲区以节省带宽资源

⑤ 一个着色器在使用了多个常量缓冲区的情况下，这些常量缓冲区相互间都不能出现同名成员

⑥ 单个常量缓冲区可以同时绑定到不同的可编程着色器阶段，因为这些缓冲区都是只读的，不会导致内存访问冲突。

一个包含常量缓冲区的*.hlsli文件同时被多个着色器文件引用，只是说明这些着色器使用相同的常量缓冲区布局，如果该缓冲区需要在多个着色器阶段使用，你还需要在C++同时将相同的常量缓冲区绑定到各个着色器阶段上

当我们在HLSL中声明常量缓冲区时，还**需要在HLSL的声明中使用关键字`register`手动指定对应的寄存器索引**，然后编译器会为对应的着色器阶段自动将其映射到15个常量缓冲寄存器的其中一个位置。这些寄存器的名字为`b0`到`b14`：

```c++ raw
/****************************** C++ ******************************/
struct VS_CONSTANT_BUFFER
{
    D3DXMATRIX mWorldViewProj;

    D3DXVECTOR4 vSomeVectorThatMayBeNeededByASpecificShader;
    float fSomeFloatThatMayBeNeededByASpecificShader;

    float fTime;

    float fSomeFloatThatMayBeNeededByASpecificShader2;
    float fSomeFloatThatMayBeNeededByASpecificShader3;
};

/***************************** HLSL *****************************/
// 在cb0中，第一个 mWorldViewProj : packoffset(c0)表示将会在这个cbuffer中的c0位置开始存储 mWorldViewProj,共使用c0,c1,c2,c3
// 由于D3DXVECTOR4 vSomeVectorThatMayBeNeededByASpecificShader占据了c4，float fSomeFloatThatMayBeNeededByASpecificShader占据了c5.x，所以float fTime就是c5.y了

// 在C++代码层中，D3DXMATRIX矩阵是行矩阵，但当矩阵从C++传递给HLSL时，HLSL默认是列矩阵的，因此传递前要进行了一次转置。如果希望不发生转置操作的话，则需要添加修饰关键字row_major
cbuffer cb0
{
    row_major float4x4 mWorldViewProj : packoffset(c0);

    float fTime : packoffset(c5.y);
};1.2.3.4.5.6.7.8.9.10.11.12.13.14.15.16.17.18.19.20.21.22.23.24.25.26.
```

注1：常量缓冲区（constant buffer views，CBV）用b寄存器来传递

注2：packoffset(c0)表示起始位置为c0，其中c为一个float4的向量(x,y,z,w)

在C++端是通过ID3D11DeviceContext::VSSetConstantBuffers、ID3D11DeviceContext::PSSetConstantBuffers指定特定的槽(slot)来给某一着色器阶段对应的寄存器索引提供常量缓冲区的数据。

如果是存在多个不同的着色器阶段使用同一个常量缓冲区，那就需要分别给这两个着色器阶段设置好相同的数据。

综合前面几节内容，下面演示了顶点着色器和常量缓冲区的用法：

```C++
cbuffer ConstantBuffer : register(b0)
{
    float4x4 g_WorldViewProj;
}

void VS_Main(
    in float4 inPos : POSITION,         // 绑定变量到输入装配器
    in uint VID : SV_VertexID,          // 绑定变量到系统生成值
    out float4 outPos : SV_Position)    // 告诉管线将该值解释为输出的顶点位置
{
    outPos = mul(inPos, g_WorldViewProj);
}1.2.3.4.5.6.7.8.9.10.11.12.13.
```

上面的代码也可以写成：

```
cbuffer ConstantBuffer : register(b0)
{
    float4x4 g_WorldViewProj;
}

struct VertexIn
{
    float4 inPos : POSITION;    // 源自输入装配器
    uint VID : SV_VertexID;        // 源自系统生成值
};

float4 VS_Main(VertexIn vIn) : SV_Position
{
    return mul(vIn.inPos, g_WorldViewProj);
}1.2.3.4.5.6.7.8.9.10.11.12.13.14.15.
```

### **纹理缓冲区（Texture Buffer）**

纹理缓冲区（tbuffer）并不是用来存储纹理的，而是指可以像纹理那样来访问其中的数据，对于索引类数据有更好的性能。这些数据也是只读的。vs、ps阶段分别最多可以绑定128个tbuffer。

```
tbuffer mytb : register(t0)
{
    float weight[256];        // 可以从CPU更新，只读
}
```

### **有类型的缓冲区(Typed Buffer)**

这是一种创建和使用起来最简单的缓冲区，其数据可以在HLSL被解释成基本HLSL类型的数组形式。

**Buffer（只读的缓冲区类型）**

**RWBuffer（可读写的缓冲区类型）**

**结构化缓冲区（Struct Buffer）**

StructuredBuffer（只读的结构化缓冲区）

```
struct TBokeh
{
    float2 Pos;
    float Radius;
    float4 Color;
};
StructuredBuffer<TBokeh> Bokeh : register( t0 );
StructuredBuffer<float> AvgLum : register( t1 );1.2.3.4.5.6.7.8.
```

RWStructuredBuffer（可读写的结构化缓冲区）

```
// Single raindrop structure
struct RainDrop
{
    float3 Pos;
    float3 Vel;
    float State;
};

// Raindrop buffer
RWStructuredBuffer<RainDrop> RainData : register( u0 );
RWStructuredBuffer<float> AverageLum : register( u1 );1.2.3.4.5.6.7.8.9.10.11.
```

### **追加/消耗缓冲区(Append/Consume Buffer)**

追加缓冲区和消耗缓冲区类型实际上是结构化缓冲区的特殊变体资源。因为涉及到修改操作，它们只能使用乱序访问视图（unordered access view，UAV）来绑定，用u寄存器来传递。

如果你只是希望这些结构体数据经过着色器变换并且不需要考虑最终的输出顺序要一致，那么使用这两个缓冲区是一种不错的选择。

AppendStructuredBuffer

```
struct TBokeh
{
    float2 Pos;
    float Radius;
    float4 Color;
};
AppendStructuredBuffer<TBokeh> BokehStack : register( u0 );

AppendStructuredBuffer<float3> g_VertexOut : register(u1);1.2.3.4.5.6.7.8.
```

ConsumeStructuredBuffer

```
ConsumeStructuredBuffer<float3> g_VertexIn : register(u0);
```

### **字节地址缓冲区(Byte Address Buffer)**

字节地址缓冲区为HLSL程序提供了一种更为原始的内存块，程序员自己负责解析内存块的内容

ByteAddressBuffer（只读的字节地址缓冲区）

使用着色器资源视图（shader resource views，SRV）来绑定，用t寄存器来传递

```
ByteAddressBuffer g_ByteAddressBuffer : register(t0);
```

RWByteAddressBuffer（可读写的结构化缓冲区）

不仅支持写入，还支持原子操作。使用乱序访问视图（unordered access view，UAV）来绑定，用u寄存器来传递。

```
RWByteAddressBuffer g_RWByteAddressBuffer : register(u0);
```

# **基础类型**

```
// 布尔型
bool b1 = true;
bool b2 = 10; // b2=true

// 32位有符号整型
int n1 = 10;
int n2 = { -25 };
int n3 = 0;
int n4 = 0.9; // 取整数部分  n4=0
int n5 = 3L; // n5=3
int n6 = 0x14; // 16进制 n6=20
int n7 = 027; // 8进制 n7=23
int n8 = b1; // n8=1

// 32位无符号整型
uint u1 = 0;
uint u2 = 1u;
uint u3 = 100L;
uint u4 = 1.5;// 取整数部分  u4=1
uint u5 = -3.2;// 赋值为负数时  u5=0
uint u6 = b1;// u6=1

// dword类型与uint类型等价
dword dw1 = 150;
dword dw2 = 0.9;// 取整数部分  dw2=0
dword dw3 = -2.8f;// 赋值为负数时  dw3=0

// 64位双精度浮点型
double d1 = 200UL;
double d2 = dw1;
double d3 = 20.8f;
double d4 = 320.5;

// 32位单精度浮点型
float f1 = -250.6;
float f2 = 130.0f;
float f3 = d3;

// 16位单精度浮点型
half h1 = 1.0f;
half h2 = n6; // h2=20
half h3 = d4; // h3=320.5
half h4 = f2; // h4=130.0f
half h5 = f1 + d1; // h5=-50.6

// 基础类型强制转换
bool b3 = bool(n3); // b3=false  支持c类型的转换方式
int n9 = int(f1); // n9=-250  支持c类型的转换方式
uint u7 = (uint)f1; // u7=0
uint u8 = (uint)d3; // u8=201.2.3.4.5.6.7.8.9.10.11.12.13.14.15.16.17.18.19.20.21.22.23.24.25.26.27.28.29.30.31.32.33.34.35.36.37.38.39.40.41.42.43.44.45.46.47.48.49.50.
```

注：有些平台可能不支持int、half和double，这种情况下，这些类型将用float来模拟

## **数组**

除了一维数组外，允许有多维数组

```
float fa1[5]; // fa1 = {0.0, 0.0, 0.0, 0.0, 0.0}
int ia1[3] = { 1 ,2 ,3 };
uint ua1[2][3] = { {2, 3, 5},{4, 8, 7} };
vector va1[2] = { {0.1, 0.2, 0.13, 0.0}, {1.0, 0.0, 2.0, 1.0} };
float1x2 ma1[2] = { {2.0, 4.0}, {0.5, 0.6} };1.2.3.4.5.
```

## **结构体（struct）**

① 可从其他结构体上派生

② 与C语言结构体一样，不允许有构造函数和析构函数

③ 不能直接对2个结构体变量进行比较

```
struct base { float param; };

struct light : base // 可从另外一个结构体上继承
{
    vector color;
    float3 position;

    //light(){} // 与C语言一样，不允许有构造函数
    //~light(){} // 与C语言一样，不允许有析构函数

    void test()
    {
        param = 0.5;
        color.x = 0.2;
    }
};

//base s1 = base(2.5); //编译错误 error X3037: constructors only defined for numeric base types
//light s2 = light(2.1, vector(1.0, 1.0, 0.0, 1.0), float3(10.0, 10.0, 0.0));//编译错误 error X3037: constructors only defined for numeric base types
light s3, s4;
//if (s3 == s4) {}// 结构体不能直接比较  编译错误 error X3020 : type mismatch

s3.test();1.2.3.4.5.6.7.8.9.10.11.12.13.14.15.16.17.18.19.20.21.22.23.
```

## **向量**

向量的分量可以为：

① {x,y,z,w} ： 用来获取顶点坐标分量

② {r,g,b,a} ： 用来获取颜色分量

从向量中可以同时抽取多个分量，这个过程称作混合（swizzle，或重组、重排）。但要注意地是，以上两种不能相互混着使用，如：xyr、rgyz等

| 分量类型 | 1维 | 2维 | 3维 | 4维 |
| --- | --- | --- | --- | --- |
| bool | bool1 // vector<bool,1> | bool2 // vector<bool,2> | bool3 // vector<bool,3> | bool4 // vector<bool,4> |
| int | int1 // vector<int,1> | int2 // vector<int,2> | int3 // vector<int,3> | int4 // vector<int,4> |
| uint | uint1 // vector<uint,1> | uint2 // vector<uint,2> | uint3 // vector<uint,3> | uint4 // vector<uint,4> |
| half | half1 // vector<half,1> | half2 // vector<half,2> | half3 // vector<half,3> | half4 // vector<half,4> |
| float | float1 // vector<float,1> | float2 // vector<float,2> | float3 // vector<float,3> | float4 // vector<float,4> 即vector |
| double | double1 // vector<double,1> | double2 // vector<double,2> | double3 // vector<double,3> | double4 // vector<double,4> |

注1：vector为一个4维向量，各元素的类型为float

注2：vector<T, n>为一个n维向量（n必须介于1~4之间），各元素的类型为T

注3：当N>n时，可裁剪降维后自动隐式转换 N --> n

```
// 向量 vector为4维float类型向量
vector v1 = { 0.0, 1.0, 0.0, 0.0 };
vector v2; // v2 = { 0.0, 0.0, 0.0, 0.0 }
v2[0] = 1.0; // v2 = { 1.0, 0.0, 0.0, 0.0 }
v2.z = 1.0; // v2 = { 1.0, 0.0, 1.0, 0.0 }
v2.g = 1.0; // v2 = { 1.0, 1.0, 1.0, 0.0 }

// 混合（swizzle）
vector v3 = v1.yzwx; // v3 = { 1.0, 0.0, 0.0, 0.0 } 等价于 v3.x=v1.y; v3.y=v1.z; v3.z=v1.w; v3.w=v1.x;
vector v4 = v1.rbga; // v4 = { 0.0, 0.0, 1.0, 0.0 }  等价于 v4.x=v1.r; v4.y=v1.b; v4.z=v1.g; v4.w=v1.a;
vector v5 = vector(0.5, 0.2, 1.0, 0.0); // v5 = { 0.5, 0.2, 1.0, 0.0 }  新构造方法
v5.xz = v1; // v5 = { 0.0, 0.2, 0.0, 0.0 }  只将v1的xz分量赋值给v5，等价于 v5.x=v1.x; v5.z=v1.z;

//vector v6 = vector(0.95); // 编译错误  error X3014: incorrect number of arguments to numeric-type constructor
vector v6 = (vector)0.95; // v6 = { 0.95, 0.95, 0.95, 0.95 }

vector<float, 4> v7 = v1; // vector<float, 4>即vector类型  v7 = { 0.0, 1.0, 0.0, 0.0 }

// 向量运算
vector v8 = { 0.2, -0.8, 0.3, 0.6 };
vector v9 = { 0.0, 0.5, 1.0, 0.2 };
vector v10 = v8 * 2; // v10 = {0.4, -1.6, 0.6, 1.2}
vector v11 = v8 + 0.6; // v11 = {0.8, -0.2, 0.9, 1.2}
vector v12 = v8 + v9; // v12 = { 0.2, -0.3, 1.3, 0.8 }
vector v13 = v8 * v9; // v13 = {0.0, -0.4, 0.3, 0.12}

// 逐分量进行比较
vector<bool, 4> v14 = (v8 > v9); // v14 = {true, false, false, true}

// 点乘(内积)
float ret1 = dot(v8, v9); // 0.2*0.0+(-0.8)*0.5+0.3*1.0+0.6*0.2 = 0.02
// 叉乘(外积)  3维向量特有
vector<float, 3> vf3Ret = cross(v8.xyz, v9.xyz); // vf3Ret.x=v8.y*v9.z-v8.z*v9.y = -0.8*1.0-0.3*0.5   = -0.95
                                                 // vf3Ret.y=v8.z*v9.x-v8.x*v9.z = 0.3*0.0-0.2*1.0    = -0.2
                                                 // vf3Ret.z=v8.x*v9.y-v8.y*v9.x = 0.2*0.5-(-0.8)*0.0 = 0.1

vector<int, 3> vi3a; // vi3a = {0, 0, 0}
vi3a.b = 10;  // vi3a = {0, 0, 10}

vector<bool, 2> vb2a; // vb2a = {false, false}
vb2a.x = true; // vb2a = {true, false}

// float4即vector
float4 vf4a; // vf4a = { 0.0, 0.0, 0.0, 0.0 }
vf4a = v2; // vf4a = { 1.0, 1.0, 1.0, 0.0 }

float1 vf1a = 0.75; // float3即vector<float,1> 即float类型
float f1 = vf1a; // f1为0.75
float f2 = vf1a.x; // f2为0.75
float f3 = vf1a.r; // f3为0.75

float2 vf2a = { 0.8, 0.9 }; // float2即vector<float,2>
float3 vf3a = { 0.2, 0.35, 0.5 }; // float3即vector<float,3>
float3 vf3b; // vf3b = { 0.0, 0.0, 0.0 }

//vf3b = vf2a; // error 编译错误  低维向量不允许赋值给高维向量
float2 vf2b = vf3a; // vf2b = { 0.2, 0.35 } 当N>n时，可裁剪降维后自动隐式转换   N --> n
vf3b = float3(vf2a, 1.0); // vf3b = { 0.8, 0.9, 1.0 }
vf3b = float3(0.3, vf2a); // vf3b = { 0.3, 0.8, 0.9 }
vf3b = float3(vf1a, vf2a); // vf3b = { 0.75, 0.8, 0.9 }
vf3b = v1;  // vf3b = { 0.0, 1.0, 0.0 };  高维向量可赋值给低维向量  后面的部分会被截断

float4 vf4b = { vf2a, vf2a }; // vf4b = { 0.8, 0.9, 0.8, 0.9 }
float4 vf4c = { 0.7, vf2a, 0.5 }; // vf4c = { 0.7, 0.8, 0.9, 0.5 }
float4 vf4d = { 0.7, vf3a }; // vf4d = { 0.7, 0.2, 0.35, 0.5 }

bool2 vb2b; // bool2即vector<bool,2>
int2 vi2a; // int2即vector<int,2>
uint2 vu2a; // uint2即vector<uint,2>
// dword2 vdw2a; // error 编译错误  不存在dword2类型
half2 vh2a; // half2即vector<half,2>
double2 vd2a; // double2即vector<double,2>
vf2a = vb2b;
vf2a = vi2a;
vf2a = vu2a;
vf2a = vh2a;
vf2a = vd2a;1.2.3.4.5.6.7.8.9.10.11.12.13.14.15.16.17.18.19.20.21.22.23.24.25.26.27.28.29.30.31.32.33.34.35.36.37.38.39.40.41.42.43.44.45.46.47.48.49.50.51.52.53.54.55.56.57.58.59.60.61.62.63.64.65.66.67.68.69.70.71.72.73.74.75.76.77.
```

## **矩阵**

按照行优先顺序来存储（行主序）

| 分量类型                                    | matrix类型 | m x n // m行n列 |
|-----------------------------------------| --- | --- |
| bool                                    | matrix<bool, m, n> | bool1x1、bool1x2、bool1x3、bool1x4……
| int                                     | matrix<int, m, n> | int1x1、int1x2、int1x3、int1x4  
| uint                                    | matrix<uint, m, n> | uint1x1、uint1x2、uint1x3、uint1x4
| half                                    | matrix<half, m, n> | half1x1、half1x2、half1x3、half1x4
| float                                   | matrix<float, m, n> | float1x1、float1x2、float1x3、float1x4
|注：matrix即为float4x4                 
| double                                  | matrix<double, m, n> | double1x1、double1x2、double1x3、double1x4 


注1：matrix为一个4x4 float矩阵

注2：matrix<T, m, n>为一个m x n（m、n必须介于1~4之间），各元素的类型为T

注3：当M>m且N>n时，可裁剪降维后自动隐式转换 M x N --> m x n

```Hlsl hlsl
float2 f2a = { 1.6, 1.8 };
float3 f3a = { 0.0, -1.0, 3.0 };
float2x2 m2x2a; // m2x2a = {0.0, 0.0, 0.0, 0.0}
float2x2 m2x2b = { 0.8, 0.6, 2.0, 0.9 }; // m2x2b = {0.8, 0.6, 2.0, 0.9}
                                         //          | 0.8  0.6 |
                                         //          | 2.0  0.9 |
float2x2 m2x2c = float2x2( f3a, 0.1 ); // m2x2c = {0.0, -1.0, 3.0, 0.1}
                                       //          | 0.0  -1.0 |
                                       //          | 3.0   0.1 |
//float2x2 m2x2d = float2x2(f2a, f3a);  // 编译出错  error X3014: incorrect number of arguments to numeric-type constructor
float2x2 m2x2e = float2x2(f2a, f3a.xz); // m2x2e = {1.6, 1.8, 0.0, 3.0}
                                        //          | 1.6  1.8 |
                                        //          | 0.0  3.0 |
//float2x2 m2x2f = float2x2(5.0); // 编译出错  error X3014: incorrect number of arguments to numeric-type constructor
float2x2 m2x2g = (float2x2)5.0; // m2x2g = {5.0, 5.0, 5.0, 5.0}
                                //          | 5.0  5.0 |
                                //          | 5.0  5.0 |

float2 f2b = m2x2b[0]; // 获取m2x2b的第1个行向量  f2b = {0.8  0.6}
float2 f2c = m2x2b[1]; // 获取m2x2b的第2个行向量  f2c = {2.0  0.9}

float f1 = m2x2b[0][1]; // 获取m2x2b的第1行第2列元素 f1 = 0.6
float f2 = m2x2b[0].y; // 获取m2x2b的第1行第2列元素 f2 = 0.6
float f3 = m2x2b[0].g; // 获取m2x2b的第1行第2列元素 f3 = 0.6
float f4 = m2x2b._m01; // 获取m2x2b的第1行第2列元素 f4 = 0.6
float f5 = m2x2b._12; // 获取m2x2b的第1行第2列元素 f5 = 0.6
float2 f2d = m2x2e._11_22 // 获取m2x2e的第1行第1列元素及第2行第2列元素 Swizzle f2d = {1.6  3.0}
m2x2e._12_21 = m2x2e._21_12; // 交换m2x2e[0][1]和m2x2e[1][0] Swizzle
                             // m2x2e = {1.6, 0.0, 1.8, 3.0}
                             //          | 1.6  0.0 |
                             //          | 1.8  3.0 |
m2x2e._m00_m11 = m2x2e._m11_m00;    // 交换M[0][0]和M[1][1]     Swizzle
                             // m2x2e = {3.0, 0.0, 1.8, 1.6}
                             //          | 3.0  0.0 |
                             //          | 1.8  1.6 |

float2x2 m2x2h = m2x2b + m2x2c; // m2x2h = {0.8, -0.4, 5.0, 1.0}
float2x2 m2x2i = m2x2b * m2x2c; // m2x2i = {0.0, -0.6, 6.0, 0.09}
float2x2 m2x2j = m2x2b + 0.2; // m2x2j = {1.0, 0.8, 2.2, 1.1}
float2x2 m2x2k = m2x2b * 2; // m2x2k = {1.6, 1.2, 4.0, 1.8}
//float2x2 m2x2l = f2a + m2x2b; // 编译错误  error X3020: type mismatch
//float2x2 m2x2m = f2a * m2x2b; // 编译错误  error X3020: type mismatch

float2x1 m2x1a = { 1.0, 0.2 }; // m2x1a = { 1.0, 0.2 }
                               //          | 1.0 |
                               //          | 0.2 |
float1x2 m1x2a = { 0.3, 1.0 }; // m1x2a = { 0.3, 1.0 }
                               //         | 0.3  1.0 |
// 矩阵算术运算  M x N --> m x n   注：当M>m且N>n时，可裁剪降维后自动隐式转换
float2x1 m2x1b = f2a + m2x1a; // float2向量可与float2x1矩阵进行算术运算
                              // m1x2b = { 2.6, 2.0 }
                              //           | 2.6 |
                              //           | 2.0 |
float1x1 m1x1a = { 0.2 }; // | 0.2 |
float3x3 m3x3a = {0.1, 0.0, 0.2, 0.15, -0.1, 0.0, -0.2, 0.0, 0.3};
                   // | 0.1   0.0  0.2 |
                   // | 0.15 -0.1  0.0 |
                   // | -0.2  0.0  0.3 |
//float2x2 m2x2n = m2x2b + m2x1a; // 编译错误  error X3017: cannot implicitly convert from 'const float2x1' to 'float2x2'
float2x1 m2x1c = m2x2b + m2x1a; // m1x2c = { 1.8, 0.8 }
float2x2 m2x2o = m2x2b + m1x1a; // m2x2o = {1.0, 0.8, 2.2, 1.1}  注：m1x1a退化为float
float2x2 m2x2p = m2x2b + m3x3a; // m2x2p = {0.9, 0.6, 2.15, 0.8}
//float3x3 m3x3b = m3x3a + m2x2b; // 编译错误 error X3017 : cannot implicitly convert from 'const float2x2' to 'float3x3'
//float3x3 m3x3c = m2x2b + m3x3a; // 编译错误 error X3017 : cannot implicitly convert from 'const float2x2' to 'float3x3'

// 矩阵-矩阵乘法
float1x1 m1x1b = mul(m1x2a, m2x1a); //                  | 1.0 |
                                    // | 0.3  1.0 | mul | 0.2 | = 0.5

float2x2 m2x2r = mul(m2x1a, m1x2a);//  | 1.0 |                    | 0.3  1.0 |
                                    // | 0.2 | mul | 0.3  1.0 | = | 0.06 0.2 |

// 矩阵右乘向量
float2x1 m2x1d = mul(m2x2b, f2a);  // f2a被当成列向量
                                   //  | 0.8  0.6 |     | 1.6 |   | 2.36 |
                                    // | 2.0  0.9 | mul | 1.8 | = | 4.82 |

// 矩阵左乘向量
float1x2 m1x2b = mul(f2a, m2x2b);  // f2a被当成行向量
                                   //                   | 0.8  0.6 |
                                   //  | 1.6  1.8 | mul | 2.0  0.9 | = | 4.88 2.58 |1.2.3.4.5.6.7.8.9.10.11.12.13.14.15.16.17.18.19.20.21.22.23.24.25.26.27.28.29.30.31.32.33.34.35.36.37.38.39.40.41.42.43.44.45.46.47.48.49.50.51.52.53.54.55.56.57.58.59.60.61.62.63.64.65.66.67.68.69.70.71.72.73.74.75.76.77.78.79.80.81.82.
```

## **纹理（texture）**

在glsl、CG或Effects Framework（效果框架）中引用纹理，只需要声明一个sampler2D。

而在HLSL中，sampler2D这个对象则被拆分为两部分：即Texture2D（纹理）和SamplerState（采样器），需要同时声明两个变量来保存它们。

**纹理**

| 类型                           | 说明 | 示例 |
|------------------------------| --- | --- |
| Texture1D                    | 1D纹理 | RWTexture1D<float> tex; |
| Texture1DArray               | 1D纹理数组 | RWTexture1DArray<float> tex; |
| Texture2D                    | 2D纹理 |
| Texture2DArray               | 2D纹理数组 | Texture2DArray<float> CascadeShadowMapTexture : register( t4 ); 
| RWTexture2DArray<float> tex; |
| Texture3D                    | 3D纹理 | RWTexture3D<float> tex; |
| Texture2DMS                  |  |  |
| Texture2DMSArray             |  |  |
| TextureCube                  |  |TextureCube<float> PointShadowMapTexture : register( t4 );|
| TextureCubeArray |  |  |
```yaml Texture2D示例
Texture2D DiffuseTexture    : register( t0 );
Texture2D<float> DepthTexture         : register( t1 );
Texture2D<float4> ColorSpecIntTexture : register( t2 );
Texture2D<float3> NormalTexture       : register( t3 );
Texture2D<float4> SpecPowTexture      : register( t4 );

RWTexture2D<float4> MyTexture : register( u0 );
• 1.
• 2.
• 3.
• 4.
• 5.
• 6.
• 7. |
```
注1：只读纹理使用着色器资源视图（shader resource views，SRV）来绑定，用t寄存器来传递

注2：可读写纹理使用乱序访问视图（unordered access view，UAV）来绑定，用u寄存器来传递 UnorderedAccessView

## **采样器**

| 类型 | 说明 | 示例 |
| --- | --- | --- |
| SamplerState | 贴图采样器 |SamplerState LinearSampler    : register( s0 );
| SamplerComparisonState | 阴影贴图采样器 | 

/////////////////////////////////////////////////////////////////////////////
// Shadow sampler
/////////////////////////////////////////////////////////////////////////////
SamplerComparisonState PCFSampler : register( s2 );
• 1.
• 2.
• 3.
• 4. |

注：采样器（sampler）用s寄存器来传递

## **示例**

在C++端是通过ID3D11DeviceContext::VSSetShaderResources、ID3D11DeviceContext::PSSetShaderResources指定特定的槽(slot)来给某一着色器阶段对应的寄存器索引提供纹理数据。

在C++端是通过ID3D11DeviceContext::VSSetSamplers、ID3D11DeviceContext::PSSetSamplers指定特定的槽(slot)来给某一着色器阶段对应的寄存器索引提供SamplerState数据。

当SamplerState不需要C++动态传入时，也可以在hlsl内部定义

```C++ ""
/****************************** C++ ******************************/
ID3D11ShaderResourceView*   g_pTexture1 = NULL;
ID3D11ShaderResourceView*   g_pTexture2 = NULL;
ID3D11SamplerState*         g_pSampLinear = NULL;
// PCF sampler state for shadow mapping
ID3D11SamplerState*         g_pPCFSamplerState = NULL;

// Create Shader Resouce View (Texture2D)
WCHAR str[MAX_PATH];
V_RETURN( DXUTFindDXSDKMediaFileCch( str, MAX_PATH, L"..\\Media\\Bokeh1.dds" ) );
V_RETURN( D3DX11CreateShaderResourceViewFromFile( g_pDevice, str, NULL, NULL, &g_pTexture1, NULL ) ); // ID3D11Device* g_pDevice;
V_RETURN( DXUTFindDXSDKMediaFileCch( str, MAX_PATH, L"..\\Media\\Bokeh2.dds" ) );
V_RETURN( D3DX11CreateShaderResourceViewFromFile( g_pDevice, str, NULL, NULL, &g_pTexture2, NULL ) ); // ID3D11Device* g_pDevice;

// Set Shader Resources
ID3D11ShaderResourceView* arrViews[2] = { g_pTexture1, g_pTexture2};
pd3dImmediateContext->PSSetShaderResources(0, 2, arrViews);// ID3D11DeviceContext* pd3dImmediateContext

// --------------------------------------------------------------

// Create sampler
D3D11_SAMPLER_DESC samDesc;
ZeroMemory( &samDesc, sizeof(samDesc) );
samDesc.Filter = D3D11_FILTER_MIN_MAG_MIP_LINEAR;
samDesc.AddressU = samDesc.AddressV = samDesc.AddressW = D3D11_TEXTURE_ADDRESS_WRAP;
samDesc.MaxAnisotropy = 1;
samDesc.ComparisonFunc = D3D11_COMPARISON_ALWAYS;
samDesc.MaxLOD = D3D11_FLOAT32_MAX;
V_RETURN( pd3dDevice->CreateSamplerState( &samDesc, &g_pSampLinear ) );

// Create the PCF sampler state
D3D11_SAMPLER_DESC samDesc2;
ZeroMemory( &samDesc2, sizeof(samDesc2) );
samDesc2.Filter = D3D11_FILTER_COMPARISON_MIN_MAG_MIP_LINEAR;
samDesc2.AddressU = samDesc2.AddressV = samDesc2.AddressW = D3D11_TEXTURE_ADDRESS_CLAMP;
samDesc2.MaxAnisotropy = 1;
samDesc2.ComparisonFunc = D3D11_COMPARISON_LESS_EQUAL;
samDesc2.MaxLOD = D3D11_FLOAT32_MAX;
V_RETURN( g_pDevice->CreateSamplerState( &samDesc2, &g_pPCFSamplerState ) );

// Set render resources
pd3dImmediateContext->PSSetSamplers( 0, 1, &g_pSampLinear ); // ID3D11DeviceContext* pd3dImmediateContext

// Set the shadowmapping PCF sampler
pd3dImmediateContext->PSSetSamplers( 2, 1, &g_pPCFSamplerState ); // ID3D11DeviceContext* pd3dImmediateContext

/***************************** HLSL *****************************/

/////////////////////////////////////////////////////////////////////////////
// Diffuse texture and linear sampler
/////////////////////////////////////////////////////////////////////////////
Texture2D    Diffuse1Texture : register( t0 );
Texture2D    Diffuse2Texture : register( t1 );
SamplerState LinearSampler : register( s0 );

SamplerComparisonState PCFSampler : register( s2 );

// sampler define in shader code
SamplerState MeshTextureSampler
{
    Filter = MIN_MAG_MIP_LINEAR;
    AddressU = Wrap;
    AddressV = Wrap;
};

float4 AmbientLightPS( VS_OUTPUT In ) : SV_TARGET0  // VS_OUTPUT In：VS的输出经过光栅化插值后，会作为输入传入PS
{
    // Sample the texture and convert to linear space
    float4 Diffuse1Color =  Diffuse1Texture.Sample( LinearSampler, In.UV );
    float4 Diffuse2Color =  Diffuse2Texture.Sample( LinearSampler, In.UV );

    // ... ...

    return float4((Diffuse1Color+Diffuse2Color).rgb, 1.0);
}1.2.3.4.5.6.7.8.9.10.11.12.13.14.15.16.17.18.19.20.21.22.23.24.25.26.27.28.29.30.31.32.33.34.35.36.37.38.39.40.41.42.43.44.45.46.47.48.49.50.51.52.53.54.55.56.57.58.59.60.61.62.63.64.65.66.67.68.69.70.71.72.73.74.75.76.
```

# **函数**

函数用法和C语言一样

函数参数限定词说明：

| 限定词 | 说明 |
| --- | --- |
| in | 缺省限定词，可以省略不写 |
| const | 当前参数为常量，不可在函数内被修改 |
| out | ① 在函数内使用前必须先初始化 ② 在函数内修改后，对外可见 |
| inout | ① 接受函数外传入的初始值 ② 在函数内修改后，对外可见 |

① 参数限定词只需要用在函数上，函数调用时不用带。

② 不允许函数递归 这一限制的原因是编译器会把函数都内联展开，以支持没有堆栈的GPU

```yaml Raw
float square(float value) // 求平方
{
    return value * value;
}

void fuc1(const float value) // const参数不能在函数内部修改
{
    //value = 0.2; // assignment to const variable value  编译错误
}

void fuc2(out float value)  // value在函数内使用前必须先初始化；在函数内修改，对外可见
{
    value = 0.0; // 注：在函数内使用out参数之前，必须先初始化，否则会编译错误
    value += 0.5;
}

void fuc3(inout float value) // value的初始值从函数外传入；在函数内修改，对外可见
{
    value += 0.5;
}

int fun4(int n)  // 直接或间接调用fun4函数，会编译报错：recursive call to function
{
    if (n == 0 || n == 1)
    {
        return 1;
    }
    return fun4(n - 1) + fun4(n - 2);
}1.2.3.4.5.6.7.8.9.10.11.12.13.14.15.16.17.18.19.20.21.22.23.24.25.26.27.28.29.
```

## **内置函数（Intrinsic Functions）**

HLSL提供了一些 [内置全局函数](https://docs.microsoft.com/en-us/windows/win32/direct3dhlsl/dx-graphics-hlsl-intrinsic-functions)，它通常直接映射到指定的着色器汇编指令集。这里只列出一些比较常用的函数：

| 函数 | 说明 | 最小支持的着色器版本 |
| --- | --- | --- |
| abs(x) | 求x的绝对值 注：x为向量或矩阵时，表示求各分量的abs | 1.1 |
| acos(x) | 求x的反余弦值 | 1.1 |
| ceil(x) | 返回不小于x的最小整数 | 1.1 |
| clamp(x, a, b) | 把x夹钳在[a, b]内 | 1.1 |
| cos(x) | 计算x的余弦值。x的单位为弧度 | 1.1 |
| cross(u,v) | 计算u、v向量的叉乘（外积） | 1.1 |
| degrees(x) | 将x从弧度转成角度 | 1.1 |
| determinant(M) | 返回矩阵的行列式det(M) | 1.1 |
| distance(u, v) | 返回两点u和v之间的距离 || u - v || | 1.1 |
| dot(u, v) | 返回向量u和v的点乘（内积） | 1.1 |
| dst(u, v) | 计算距离向量 | 5.0 |
| floor(x) | 返回不大于x的最大整数 | 1.1 |
| length(v) | 返回向量v的模 || v || | 1.1 |
| lerp(u, v, t) | 在u和v之间做线性插值，并返回t所在比例的值 注：t在[0,1]之间 | 1.1 |
| log(x) | 返回ln(x) 注：以e为底数的对数值 | 1.1 |
| log10(x) | 返回以10为底数的对数值 | 1.1 |
| log2(x) | 返回以2为底数的对数值 | 1.1 |
| max(x, y) | 返回x，y中的较大的一个 | 1.1 |
| min(x, y) | 返回x，y中的较小的一个 | 1.1 |
| mul(M, N) | 矩阵乘法 
若M为向量，被视为行向量；若N为向量，被视为列向量 | 1.1 |
| normalize(v) | 对向量v归一化，返回v / || v || | 1.1 |
| pow(b, n) | 返回b的n次幂 | 1.1 |
| radians(x) | 将x从角度转为弧度 | 1 |
| reflect(v, n) | 给定入射向量v和表面法线n时，求出反射向量 | 1 |
| refract(v, n, eta) | 给定折射向量v、表面法线n及两种材质的折射度索引的比率eta，求出折射向量 
详见：斯涅耳定律（Snell's Law） | 1.1 |
| rsqrt(x) | 返回1/sqrt(x) | 1.1 |
| saturate(x) | 返回clamp(x, 0.0, 1.0) | 1 |
| sin(x) | 计算x的正弦值。x的单位为弧度 | 1.1 |
| sincos(in x, out s, out c) | 计算x的正弦值s和余弦值c。x的单位为弧度 | 1.1 |
| sqrt(x) | 对x开根号 | 1.1 |
| tan(x) | 返回x的正切值。x的单位为弧度 | 1.1 |
| transpose(M) | 返回矩阵M的转置矩阵 | 1 |

# **参考**

DirectX11--HLSL语法入门 （csdn）

DirectX11--深入理解HLSL常量缓冲区打包规则

DirectX11--深入理解与使用缓冲区资源

contant buffer中的packoffset

DirectX11 With Windows SDK--03 索引缓冲区、常量缓冲区

在DirectX10中不使用Effect框架处理Shader与程序间的数据传递

[https://docs.microsoft.com/en-us/windows/win32/direct3d9](https://docs.microsoft.com/en-us/windows/win32/direct3d9)

[https://docs.microsoft.com/en-us/windows/win32/direct3d10](https://docs.microsoft.com/en-us/windows/win32/direct3d10)

[https://docs.microsoft.com/en-us/windows/win32/direct3d11](https://docs.microsoft.com/en-us/windows/win32/direct3d11)

[https://docs.microsoft.com/en-us/windows/win32/direct3d12](https://docs.microsoft.com/en-us/windows/win32/direct3d12)