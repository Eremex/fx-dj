This example demonstrates how to use fx-mgr in FLAT mode. The configurator searches interfaces and their implementations, and after application model is built, all the files to be compiled are copied into specified folder. Headers are also renamed (to exectly match their interface name). This trick with header renaming allows to define import macro just as follows:
#define FX_INTERFACE(i) <i.h>
No additional code is needed. This is why this mode is called "flat": all the files are copied into single folder and application has the flat structure.
This mode is useful when the application should be provided in sources what is common in embedded world in order to allow the customer to use any tools and avoid inter-compiler compatibility problems. Developer may have any source directory structure, but deployed package contain flat sources list, no need to adjust includes paths and so on.
The example contain three modules: hello, world and main. Main module imports abstract interfaces hello and world and prints a string which is built by the imported modules. 
Be sure that msbuild, cl (Microsoft C compiler from the Visual Studio) and fx_mgr executables are accessible.
How to run the example:
1) Set current directory as example directory (where the .proj file is located)
2) Type msbuild (helloworld.exe should appear in current folder).