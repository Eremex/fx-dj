This example demonstrates how to use fx-mgr with common header. The configurator searches interfaces and their implementations and after application model is built the common header (which maps module names to header files) is generated. This header is implicitly included into all source files in compiler command line. This is why "#include" directives know about FX_INTERFACE macro and module names.
The example contain three modules: hello, world and main. Main module imports abstract interfaces hello and world and prints a string which is built by the imported modules. 
Be sure that msbuild, cl (Microsoft C compiler from the Visual Studio) and fx_mgr executables are accessible.
How to run the example:
1) Set current directory as example directory (where the .proj file is located)
2) Type msbuild (helloworld.exe should appear in current folder).