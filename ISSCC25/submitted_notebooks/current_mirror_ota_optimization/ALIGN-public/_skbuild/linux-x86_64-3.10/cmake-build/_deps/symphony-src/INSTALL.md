## BUILDING AND INSTALLING

These instructions are for building and installing SYMPHONY from source. For
instructions on how to obtain pre-built binaries, please see the README file.
The instructions here are for the standard build. For a more detailed
explanation of the build options and for building in parallel, see the
SYMPHONY [manual](

IMPORTANT: The build instructions have changed significantly. In most case,
you do not need to clone this repository first! Please follow the instructions
for your platform below.

### Building on Linux

Most Linux distributions come with all the required tools installed. To obtain
the source code, the first step is to get the installer that will then
fetch the source for SYMPHONY and all its dependencies. *You do not need to
clone SYMPHONY first, just do the following!* Open a terminal and execute

```
git clone https://www.github.com/coin-or/COIN-OR-OptimizationSuite
```

Next, to check out source code for and build all the necessary projects
(including dependencies), execute the script in the `COIN-OR-OptimizationSuite`
subdirectory. To execute the script, do

```
cd COIN-OR-OptimizationSuite
chmod u+x coin.install.sh
./coin.install.sh
```

(Note: The `chmod` command is only needed if the execute permission is not
automatically set by git on cloning). Once you run the script,
you will be prompted interactively to select a project to fetch and build. The
rest should happen automagically. Alternatively, the following command-line
incantation will execute the procedure non-interactively.

```
./coin.install.sh fetch build --no-prompt --main-proj=SYMPHONY
```

Options that would have been passed to the `configure` script under the old
build system can simply be added to the command-line. For example, to build
with debugging symbols, do

```
./coin.install.sh fetch build --no-prompt --main-proj=SYMPHONY --enable-debug
```

To get help with additional options available in running the script, do

```
./coin/install.sh --help
```

The above procedures will build all required dependencies and SYMPHONY itself.
Afterwards, the binaries will be installed in the directory `Mibs/build/bin`
and the libraries in the directory `SYMPHONY/build/lib`. If you wish to
install in a different directory, such as `/usr/local`, then run the command

```
./coin.install.sh install --no-prompt --main-proj=SYMPHONY --prefix=/path/to/install/dir
```

After installation, you will also need to add `/path/to/install/dir/bin` to your
`PATH` variable in your `.bashrc` and also add `/path/to/install/dir/lib`
to your `LD_LIBRARY_PATH` if you want to link to COIN libraries. 

### Building on Windows (MSys2/CYGWIN and MinGW/MSVC)

By far, the easiest way to build on Windows is with the GNU autotools and the
GCC compilers. The first step is to install either
   * [Msys2](https://msys2.github.io/)
   * [CYGWIN](http://cygwin.org/)
   * [Windows Subsystem for Linux](https://docs.microsoft.com/en-us/windows/wsl/install-win10)

If you don't already have CYGWIN installed and don't want to fool around with
WSL (which is a great option if you already know your way around Unix), it is
recommended to use MSys2, since it provides a minimal toolset that is easy to
install. To get MSys2, either download the installer
[here](https://msys2.github.io/) or download and unzip MSys2 base from
[here](http://kent.dl.sourceforge.net/project/msys2/Base/x86_64/msys2-base-x86_64-20190512.tar.xz) 
(this is an out-of-date version, there may be a better place to get an archive
version). 

Following any of the above steps, you should have the `bash` command
(with Msys2, be sure to run `msys2_shell.bat` 
or manually add `msys64\usr\bin`, `msys64\mingw32\bin`, and
`msys64\mingw64\bin` to your Windows path).   

Once you have bash installed and in your `PATH`, open a Windows terminal and
type 

```
bash
pacman -S make wget tar patch dos2unix diffutils git svn
```

To obtain the source code, the first step is to get the installer that will then
fetch the source for SYMPHONY and all its dependencies. *You do not need to
clone SYMPHONY first, just do the following!* Open a terminal and execute

```
git clone https://www.github.com/coin-or/COIN-OR-OptimizationSuite
```

Next, to check out source code for and build all the necessary projects
(including dependencies), execute the script in the `COIN-OR-OptimizationSuite`
subdirectory. To execute the script, do

```
cd COIN-OR-OptimizationSuite
chmod u+x coi.install.sh
./coin.install.sh
```

(Note: The `chmod` command is only needed if the execute permission is not
automatically set by git on cloning). Once you run the script,
you will be prompted interactively to select a project to fetch and build. the
rest should happen automagically. Alternatively, the following command-line
incantation will execute the procedure non-interactively.

```
./coin.install.sh fetch build --no-prompt --main-proj=SYMPHONY
```
Options that would have been passed to the `configure` script under the old
build system can simply be added to the command-line. For example, to build
with debugging symbols, do

```
./coin.install.sh fetch build --no-prompt --main-proj=SYMPHONY --enable-debug
```

To get help with additional options available in running the script, do

```
./coin/install.sh --help
```

To use the resulting binaries and/or libraries, you will need to add the
full path of the directory `build\bin` to your Windows executable
search `PATH`, or, alternatively, copy the conents of the build directory to 
`C:\Program Files (x86)\SYMPHONY` and add the directory
`C:\Program Files (x86)\SYMPHONY\bin` 
to your Windows executable search `PATH`. You may also consider adding
`C:\Program Files (x86)\SYMPHONY\lib` to the `LIB` path and 
`C:\Program Files (x86)\SYMPHONY\include` to the `INCLUDE` path. 

It is possible to use almost the exact same commands to build with the Visual
Studio compilers. Before doing any of the above commands in the Windows
terminal, first run the `vcvarsall.bat` script for your version of Visual
Studio. Note that you will also need a compatible Fortran compiler if you want
to build any projects requiring Fortran (`ifort` is recommended, but not
free). Then follow all the steps above, but replace the `build` command
with

```
./coin.install.sh fetch build --no-prompt --main-proj=SYMPHONY --enable-msvc
```

## BUILDING WITH the MSVC++ IDE

These instructions are for MSVC++ Version 10. Instructions for other versions
should be similar. '''The MSVC++ are not regularly tested so please let us
know if they are broken.'''

1. Go to `SYMPHONY/MSVisualStudio/v10` directory and open the solution
file `symphony.sln`.

2. Note that there are a number of additional preprocessor definitions that
control the functionality of SYMPHONY. These definitions are described in
`sym.mak`, a Unix-style makefile included in the distribution. To enable
the functionality associated with a particular definition, simply add it to
the list of definitions of `libSymphony` project together with the
required libraries and paths. For instance, if you want to enable GMPL reader
option, you need to * add the directory of the header files of GLPK to the
include files path * add `USE_GLPMPL` to the defines * add the GLPK
library to the solution

3. Make sure that the project `symphony` is set as the startup project by
choosing "Set as Startup Project" from the Project menu after selecting the
symphony project in the Solution Explorer. Choose `Build Solution` from
the `Build` menu. This should successfully build the SYMPHONY library and
the corresponding executable.

4. To test the executable, go to the `Debug` tab and choose `Start
Without Debugging.` and then type `help` or `?` to see a list of
available commands.

## BUILDING WITH VISUAL STUDIO FROM COMMAND LINE (deprecated)
  
These instructions are for MSVC++ Version 10. Instructions for other versions
should be similar.

1. Open a command line terminal. Go to 'SYMPHONY/MSVisualStudio/v10'
directory and type

```
devenv symphony.sln /Build "Debug|Win32
```

This will create the 32-bit debug version of SYMPHONY. You can build 64-bit
with

```
devenv symphony.sln /Build "Debug|x64"
```

For each command, the library `libSymphony.lib` and the executable
`symphony` will be created in directories according to platform and
configuration. The library, together with the header files in
`SYMPHONY\include\`, can then be used to call SYMPHONY from any C/C++
code. The API for calling SYMPHONY is described in the user's manual.

2. To test the executable, type

```
symphony.exe -F ..\..\SYMPHONY\Datasets\sample.mps
```

In the appropriate directory. If you want to use the interactive optimizer,
simply type

```
symphony.exe
```

and then type `help` or `?` to see a list of available commands.

3. If SYMPHONY is modified, type

```
devenv symphony.sln /Rebuild "Debug|Win32"
```

in order to clean and rebuild everything.

## BUILDING WITH THE NMAKE Utility (deprecated)

Note: the `sym.mak` file is no longer maintained, but may work.

1. Go to `MSVisualStudio` directory and edit the `sym.mak` makefile
to reflect your environment. This involves specifying the LP solver to be
used, assigning some variables and setting various paths. Only minor edits
should be required. An explanation of what has to be set is contained in the
comments in the makefile. Note that, you have to first create the COIN
libraries Cgl, Clp, Osi, OsiClp and CoinUtils.

2. Once configuration is done, open a command line terminal and type

```
nmake sym.mak
```

This will make the SYMPHONY library `libSymphony.lib` and the executable
`symphony` in `Debug` directory. The library, together with the header
files in `SYMPHONY\include\`, can then be used to call SYMPHONY from any
C/C++ code. The API for calling SYMPHONY is described in the user's manual.

3. To test the executable, type

```
symphony.exe -F ..\..\SYMPHONY\Datasets\sample.mps
```

in the output directory. If you want to use the interactive optimizer, simply
type

```
symphony.exe
```
and then type `help` or `?` to see a list of available commands.

### Building on OS X

OS X is a Unix-based OS and ships with many of the basic components needed to
build COIN-OR, but it's missing some things. For examples, the latest versions
of OS X come with the `clang` compiler but no Fortran compiler. You may also
be missing the `wget` utility and `subversion` and `git` clients (needed for
obtaining source code). The easiest way to get these missing utilitites is to
install Homebrew (see http://brew.sh). After installation, open a terminal and
do

```
brew install gcc wget svn git
```

To obtain the source code, the first step is to get the installer that will then
fetch the source for SYMPHONY and all its dependencies. *You do not need to
clone SYMPHONY first, just do the following!* Open a terminal and execute

```
git clone https://www.github.com/coin-or/COIN-OR-OptimizationSuite
```

Next, to check out source code for and build all the necessary projects
(including dependencies), execute the script in the `COIN-OR-OptimizationSuite`
subdirectory. To execute the script, do

```
cd COIN-OR-OptimizationSuite
chmod u+x coi.install.sh
./coin.install.sh
```

(Note: The `chmod` command is only needed if the execute permission is not
automatically set by git on cloning). Once you run the script,
you will be prompted interactively to select a project to fetch and build. the
rest should happen automagically. Alternatively, the following command-line
incantation will execute the procedure non-interactively.

```
./coin.install.sh fetch build --no-prompt --main-proj=SYMPHONY
```

With this setup, `clang` will be used for compiling C++ by default and
`gfortran` will be used for Fortran. Since `clang` uses the GNU standard
library, `gfortran` is compatible.

If you want to use the `gcc` compiler provided by Homebrew, then replace the
`build` command above with

```
./coin.install.sh build --no-prompt --main-proj=SYMPHONY CC=gcc-5 CXX=g++-5
```

Options that would have been passed to the `configure` script under the old
build system can simply be added to the command-line. For example, to build
with debugging symbols, do

```
./coin.install.sh fetch build --no-prompt --main-proj=SYMPHONY --enable-debug
```

To get help with additional options available in running the script, do

```
./coin/install.sh --help
```

If you wish to install in a different directory, such as `/usr/local`, then run
the command

```
./coin.install.sh install --no-prompt --main-proj=SYMPHONY --prefix=/path/to/install/dir
```

After installation, you will also need to add `/path/to/install/dir/bin` to your
`PATH` variable in your `.bashrc` and also add `/path/to/install/dir/lib`
to your `DYLD_LIBRARY_PATH` if you want to link to COIN libraries. 

