This example demonstrates how to use dependency injection in fx-mgr. 
The example contain four modules: 
  hello, world (modules which are used to get some strings), 
  main module (which gets and concatenate those strings and outputs them) 
  and output module (which abstracts the output method). 
There are two possible implementations of the output: console print and message box. Source files have no knowledge about actual output implementation.
Since there is more than one implementation of interface "output", the configurator needs a hint which one should be used, this hint is provided by the mapping file (with *.map extension).
Be sure that msbuild, cl (Microsoft C compiler from the Visual Studio) and fx_mgr executables are accessible.
How to run the example:
1) Set current directory as example directory (where the .proj file is located)
2) Type msbuild (helloworld.exe should appear in current folder).