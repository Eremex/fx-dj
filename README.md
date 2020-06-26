FX-DJ
-----

Compile-time dependency injection tool for C/C++.

How it works
------------

### Component description

Each source file has metadata entry describing component affiliation. There are two types of metadata: interface tag and implementation tag. They are written in YAML format inside braces of macro FX_METADATA((...)). The macro is not used during compilation, so, its content does not affect other code in any way. Interface tag may be written only in header files (only one header per component is allowed within the project):

    FX_METADATA(({ interface: [MY_INTERFACE_NAME, MY_IMPLEMENTATION_NAME] }))

Implementation tags is written inside source (.c or .cpp) files. There may be zero or more source files corresponding to header with the same implementation tag.

    FX_METADATA(({ implementation: [MY_INTERFACE_NAME, MY_IMPLEMENTATION_NAME] }))

This approach enables component view of source code: all files containing the tag with same names of interface and implementation may be considered as a component.

#### Using components

The key distinction from existing dependency injection tools is dependency description. Instead of specifying dependencies in separate files we use it just as regular C 'include' with component name as a parameter.

    #include FX_INTERFACE(MY_INTERFACE_NAME)

Inclusion of interface MY\_INTERFACE\_NAME results in inclusion of header file containing MY\_INTERFACE\_NAME interface tag. Further it allows to find all source files to be built by implementation name. This process relies in C preprocessor for dependency tracking and works with any standard C compiler. When metadata is read from all files in source folders the tool generates "common header" file containing interface-to-path mapping. Such mapping is a set of 'defines' like:

    #define MY_INTERFACE_NAME____MY_IMPLEMENTATION_NAME "c:\sources\example.h"

If there is only one implementation for some component type, then interface name is directly mapped to that component.

    #define MY_INTERFACE_NAME MY_INTERFACE_NAME____MY_IMPLEMENTATION_NAME

To get dependencies from any source file we have to preprocess it with C preprocessor with "common header" included. After all "includes" are substututed with corresponding header content the metadata tag from that header appear in output and may be analyzed by the tool.

#### Dependency injection

If there are more than one implementation of some interface (same interface name but different implementation name) then component may be altered with external injection file containing strings like:

    MY_INTERFACE_NAME = ALTERNATE_IMPLEMENTATION

This line means that implementation MY\_IMPLEMENTATION\_NAME should be used for interface MY\_INTERFACE\_NAME. Technically injection works by adding additional lines into "common header".

    #define MY_INTERFACE_NAME MY_INTERFACE_NAME____ALTERNATE_IMPLEMENTATION

Using FX-DJ
-----------

Prerequisites:
FX-DJ requires C preprocessor allowing arbitrary files to be included via command line. The environment variable with name FX_PREP should be set to value in printf format where first component is an 'force include' file and second is a file to preprocess. Preprocessor should write into stdout.
Example for GNU GCC:

    gcc <options and include search paths> -include %s %s

FX-DJ tests preprocessor on startup and will not work if this variable is not set or set incorrectly.

    fx-dj.py -p Path -t Target -a Alias -o Output [-m Header] [-v]

- **Path**:
  List of paths separated by comma where source code containing described metadata is located.
- **Target**:
  Target interface name (i.e. MY_INTERFACE_NAME in previous example).
- **Alias**:
  File containing interface to implementation mapping for interfaces with more than one implementation.
- **Output**:
  If this is some existing folder then sources implementing target interface will be copied into, otherwise new output file will be created. The file contains paths to files implementing the target.
- **Header**:
  Save "common header" containing paths to headers. It may be needed for compilation to use FX_INTERFACE macro in 'includes'.
- **v**:
  Enables verbose output.

Limitations
-----------

Current version is very simple and does not contain full-featured YAML parser. Since metadata may only contain single tag with non-recursive structure it may be searched by regular expressions only.

Getting Started
---------------

FX-DJ requires python interpreter to be installed on machine. Both versions of python are supported (2 and 3). However version 3 is recommended since the tool uses data structures and methods which are inefficient in python 2.

License
-------

3-clause BSD. See header in main script file for details.
