---
title: GPU
date: 2022-04-07 12:00
tags:
- 笔记
- GPU
category: 图形学笔记
count: true
---
# GPU

## SIMD

![Untitled](GPU%206cd925943e86431ca3394bb5322ef184/Untitled.png)

SIMD (Single Instruction Multiple Data)

单指令多数据，例如多维向量 ，c++ 里**SSE就是调用单指令多数据**

SIMT(single Instruction Multiple Threads)

单指令多线程，可对GPU中单个SM中的多个Core同时处理同一指令，并且每个Core存取的数据可以是不同的。

![Untitled](GPU%206cd925943e86431ca3394bb5322ef184/Untitled%201.png)

GPC(图形处理集群) 计算、栅格化、阴影和纹理处理。40系列安培架构里面还塞了AI，还有光追

- **SM**  (流式多处理器)      运行CUDA内核的GPU的一部分
    - SFU（Special function units）执行特殊数学运算（sin、cos、log等）
    - **Texture Units**   纹理处理单元，它可以获取和过滤纹理。
    - **CUDA Core**  允许不同处理器同时工作数据的并行处理器，也叫流处理器Stream Processor
    - Warp Schedulers：这个模块负责warp调度，一个warp由32个线程组成，warp调度器的指令通过Dispatch Units送到Core执行。
    - LD/ST（load/store）模块来加载和存储数据

![Untitled](GPU%206cd925943e86431ca3394bb5322ef184/Untitled%202.png)

GPU被划分成多个GPCs(Graphics Processing Cluster)，每个GPC拥有多个SM（SMX、SMM）和一个光栅化引擎(Raster Engine)，它们其中有很多的连接，最显著的是Crossbar，它可以连接GPCs和其它功能性模块（例如ROP或其他子系统）。

程序员编写的shader是在SM上完成的。每个SM包含许多为线程执行数学运算的Core（核心）。例如，一个线程可以是顶点或像素着色器调用。这些Core和其它单元由Warp Scheduler驱动，Warp Scheduler管理一组32个线程作为Warp（线程束）并将要执行的指令移交给Dispatch Units。

# ****GPU逻辑管线****

1、程序通过图形API(DX、GL、WEBGL)发出drawcall指令，指令会被推送到驱动程序，驱动会检查指令的合法性，然后会把指令放到GPU可以读取的Pushbuffer中。

2、经过一段时间或者显式调用flush指令后，驱动程序把Pushbuffer的内容发送给GPU，GPU通过主机接口（Host Interface）接受这些命令，并通过前端（Front End）处理这些命令。

3、在图元分配器(Primitive Distributor)中开始工作分配，处理indexbuffer中的顶点产生三角形分成批次(batches)，然后发送给多个PGCs。这一步的理解就是提交上来n个三角形，分配给这几个PGC同时处理。

4、在GPC中，每个SM中的Poly Morph Engine负责通过三角形索引(triangle indices)取出三角形的数据(vertex data)，即图中的Vertex Fetch模块。

5、在获取数据之后，在SM中以32个线程为一组的线程束(Warp)来调度，来开始处理顶点数据。Warp是典型的单指令多线程（SIMT，SIMD单指令多数据的升级）的实现，也就是32个线程同时执行的指令是一模一样的，只是线程数据不一样，这样的好处就是一个warp只需要一个套逻辑对指令进行解码和执行就可以了，芯片可以做的更小更快，之所以可以这么做是由于GPU需要处理的任务是天然并行的。

6、SM的warp调度器会按照顺序分发指令给整个warp，单个warp中的线程会锁步(lock-step)执行各自的指令，如果线程碰到不激活执行的情况也会被遮掩(be masked out)。被遮掩的原因有很多，例如当前的指令是if(true)的分支，但是当前线程的数据的条件是false，或者循环的次数不一样（比如for循环次数n不是常量，或被break提前终止了但是别的还在走），因此在shader中的分支会显著增加时间消耗，在一个warp中的分支除非32个线程都走到if或者else里面，否则相当于所有的分支都走了一遍，线程不能独立执行指令而是以warp为单位，而这些warp之间才是独立的。

7、warp中的指令可以被一次完成，也可能经过多次调度，例如通常SM中的LD/ST(加载存取)单元数量明显少于基础数学操作单元。

8、由于某些指令比其他指令需要更长的时间才能完成，特别是内存加载，warp调度器可能会简单地切换到另一个没有内存等待的warp，这是GPU如何克服内存读取延迟的关键，只是简单地切换活动线程组。为了使这种切换非常快，调度器管理的所有warp在寄存器文件中都有自己的寄存器。这里就会有个矛盾产生，shader需要越多的寄存器，就会给warp留下越少的空间，就会产生越少的warp，这时候在碰到内存延迟的时候就会只是等待，而没有可以运行的warp可以切换。

9、一旦warp完成了vertex-shader的所有指令，运算结果会被Viewport Transform模块处理，三角形会被裁剪然后准备栅格化，GPU会使用L1和L2缓存来进行vertex-shader和pixel-shader的数据通信。

10、接下来这些三角形将被分割，再分配给多个GPC，三角形的范围决定着它将被分配到哪个光栅引擎(raster engines)，每个raster engines覆盖了多个屏幕上的tile，这等于把三角形的渲染分配到多个tile上面。也就是像素阶段就把按三角形划分变成了按显示的像素划分了。

11、SM上的Attribute Setup保证了从vertex-shader来的数据经过插值后是pixel-shade是可读的。

12、GPC上的光栅引擎(raster engines)在它接收到的三角形上工作，来负责这些这些三角形的像素信息的生成（同时会处理裁剪Clipping、背面剔除和Early-Z剔除）。

13、32个像素线程将被分成一组，或者说8个2x2的像素块，这是在像素着色器上面的最小工作单元，在这个像素线程内，如果没有被三角形覆盖就会被遮掩，SM中的warp调度器会管理像素着色器的任务。

14、接下来的阶段就和vertex-shader中的逻辑步骤完全一样，但是变成了在像素着色器线程中执行。 由于不耗费任何性能可以获取一个像素内的值，导致锁步执行非常便利，所有的线程可以保证所有的指令可以在同一点。

15、最后一步，现在像素着色器已经完成了颜色的计算还有深度值的计算，在这个点上，我们必须考虑三角形的原始api顺序，然后才将数据移交给ROP(render output unit，渲染输入单元)，一个ROP内部有很多ROP单元，在ROP单元中处理深度测试，和framebuffer的混合，深度和颜色的设置必须是原子操作，否则两个不同的三角形在同一个像素点就会有冲突和错误。

# GPu渲染架构

## **IMR(Immediate Mode Rendering) 立即渲染**

![Untitled](GPU%206cd925943e86431ca3394bb5322ef184/Untitled%203.png)

![Untitled](GPU%206cd925943e86431ca3394bb5322ef184/Untitled%204.png)

IMR模式的GPU的优势在于，顶点着色器和其它几何体相关着色器的输出可以保留在GPU内的芯片上。这些着色器的输出可以存储在FIFO缓冲区，直到管道中的下一阶段准备使用数据，GPU可以使用很少的外部内存带宽存储和检索中间几何结果。

IMR模式的GPU的劣势在于，像素着色在屏幕上跳跃，因为三角形按绘制顺序处理，数据流中的任何三角形都可能覆盖屏幕的任何部分（下图）。意味着活动工作集是整个framebuffer的大小。例如，考虑一个分辨率为1440p的设备，使用32位每像素(BPP)的颜色，32位每像素的填充深度/模板，将提供30MB的总工作集，若全部存储在on chip上，数据量过大，因此必须存储在DRAM的off chip之外。

## **TBR（Tile Based Rendering）**

![Untitled](GPU%206cd925943e86431ca3394bb5322ef184/Untitled%205.png)

TBR架构的GPU会把整个逻辑渲染管线**打断成两个阶段：**

第一阶段和IMR类似，它负责顶点处理的工作，不同的是在每个三角形执行完他们的VS之后，还会执行一个称之为**Binning Pass**[[18]](https://zhuanlan.zhihu.com/p/68158277#ref_18)的阶段，这个阶段把framebuffer切分成若干个小块（Tiles/Bins），根据每个三角形在framebuffer上的空间位置，把它的引用写到受它影响的那些Tiles里面，同时由VS计算出来的用于光栅化和属性插值的数据，则写入另一个数组（**我们可以认为图中Primitive List就是我们说的一个固定长度数组，其长度依赖于framebuffer划分出的tile的数量，数组的每个元素可以认为是一个linked list，存的是和当前tile相交的所有三角形的指针，而这个指针指向的数据，就是图中的Vertex Data，里面有VS算出的pos和varying变量等数据**）。在Bining Pass阶段，**Primitive List和Vertex Data的数据会被写回到System Memory里**

TBR的管线会等待同一个framebuffer上所有的三角形的第一阶段都完成后，才会进入到第二阶段，这就表示，**你应该尽可能的少切换framebuffer，让同一个framebuffer的所有三角形全部绘制完毕再去切换**

第二阶段负责像素着色，这一阶段将会**以Tile为单位去执行（而非整个framebuffer）** ，每次Raster会从Primitive List里面取出一个tile的三角形列表，然后根据列表对当前tile的所有三角形进行光栅化以及顶点属性的插值。后面的阶段TBR和IMR基本是一致的，唯一区别在于，由于Tile是比较小的，**因此每个Tile的color buffer/depth buffer是存储在一个on chip memory上，所以整个着色包括z test的过程，都是发生在on chip memory上，直到整个tile都处理完毕后，最终结果才会被写回System Memory**。

```cpp
# Pass one
for draw in renderPass:
    for primitive in draw:
        for vertex in primitive:
            execute_vertex_shader(vertex)
        if primitive not culled:
            append_tile_list(primitive)

# Pass two
for tile in renderPass:
    for primitive in tile:
        for fragment in primitive:
            execute_fragment_shader(fragment)
```

**分块（Binning Pass）**过程大致如下：

![Untitled](GPU%206cd925943e86431ca3394bb5322ef184/Untitled%206.png)

- 设定每个Bin（也被称为Tile）的固定大小（2的N次方，长宽通常相同，具体尺寸因GPU厂商而异，如16x16、32x32、64x64），根据Frame Buffer尺寸设置可见数据流。
- 转换图元坐标。注意此阶段处理的是索引和顶点数据，某些GPU（如Adreno）会用特殊的简化过的shader（而非完整的Vertex Shader）来处理坐标，以减少带宽和能耗。此阶段通常只有顶点的位置有效，其它顶点数据（纹理坐标、法线、切线、顶点颜色）都会被忽略。
- 遍历所有图元，标记所有图元覆盖到的块，将可见性数据写入到被覆盖的块数据流中。
- 将可见性数据流写回系统显存中。

**渲染（Rendering Pass）**过程大致如下：

- 初始化渲染Pass。
- 遍历所有分块，对每个分块执行以下操作：
    - 利用分块的可见性数据流，执行绘制调用。
    - 光栅化图元。
    - 像素操作（像素着色器、深度模板测试、Alpha测试、混合）。
    - 写入像素数据（颜色、深度、模板等等）到分块芯片上的缓冲区（又被称为On-Chip Memory、GMEM、Tiled Memory）。

**解析（Resolve Pass）**阶段过程如下：

- 如果开启了MSAA，在GMEM上的解析颜色、深度等数据（求平均值）。可以减少后续步骤GMEM传输到系统显存的数据总量。
    
    ![https://img2020.cnblogs.com/blog/1617944/202111/1617944-20211112221626907-2059546161.png](https://img2020.cnblogs.com/blog/1617944/202111/1617944-20211112221626907-2059546161.png)
    
- 将分块上的所有像素数据（颜色、深度、模板等）写入到系统显存中。
- 如果不是Frame Buffer的最后一个分块，继续执行下一个分块。
- 如果是Frame Buffer的最后一个分块，交互缓冲区，执行下一帧的Binning Pass。

## **TBDR（Tile Based Deferred Rendering）延迟渲染**

- 使用的是延迟渲染（Deferred Rendering）
- HSR（Hidden Surface Removal，隐藏面消除）等进一步减少了不需要渲染的过程

![Untitled](GPU%206cd925943e86431ca3394bb5322ef184/Untitled%207.png)

[ ****深入GPU和渲染优化（基础篇）****](https://www.notion.so/GPU-d4b709561b4345e4b120236c4dd265f4)