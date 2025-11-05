# Introduction

The layout design of analog integrated circuits remains one of the most demanding stages in the design flow \cite{Scheible2015}. Generating a layout that satisfies design rule checks (DRC) and layout versus schematic (LVS) verification is time-consuming when performed manually. Recent approaches aiming for full automation include large language models and reinforcement learning-based optimizers. Although these approaches are promising and aim for full automation, they rely on complex models that require substantial computational resources, limiting their practical applicability and requiring training from implemented layout designs.

In this context, an intermediate approach is proposed that combines designer interaction with a semi-automatic layout generation flow, implemented in Python on top of the open-source GLayout framework. This type of work can be used to train AI models. The methodology reduces layout design time through structured configuration inputs, such as matrices that define transistor placement, along with dictionaries that describe device parameters. The methodology is validated through a current reference generator design, implemented in the GF180 PDK, demonstrating the adaptability of the methodology. This work implements the complete flow through the open-source container [IIC-OSIC-TOOLS](https://github.com/Jianxun/iic-osic-tools-project-template), which integrates all the necessary tools for each design step, ensuring consistency across design stages and enabling advanced analyses.

![Flow](figures/AutoDesignFlow.png)

# Submitted Notebook

Here you will find the notebook called `CodeChip.ipynb`, which contains the code to generate the layout of the current reference generator.

Also, here is a picture of the generated layout in png format (is generated in svg):

![CurrentReferenceLayout](layouts/out.png)

# IIC-OSIC-TOOLS Container

This work has been developed inside a Docker container, from the [IIC-OSIC-TOOLS](https://github.com/Jianxun/iic-osic-tools-project-template) template repository. If you don't have the container, please follow the instructions for instalation, to runthe execution of scripts and the notebook.

# The Complete Work (with Schematics, Layout Generation, and Verification)

To see the complete work, please clone the following repository inside the container:

```
> cd /foss/designs/
> git clone https://github.com/AlexMantilla1/Onchip_CurRefGen.git
```

This work uses Xschem for schematic design. All related schematics are in the folder `/foss/designs/Onchip_CurRefGen/designs/libs/*/xschem`.