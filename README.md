# fx-dj
Compile-time dependency injection tool for C/C++

## Purpose
The tool is created to bring complexity management in large self-contained
projects:
- Increase abstraction level
- Component view of code
- Code reuse
- Srcs are not affected by adding new components
- Independent component testing

## How it works
1. Each source file has metadata with describes component affiliation.
2. Include file names in sources are replaced by include components.
3. Tool generates list of files to be build for particular configuration.
4. User selects interface implementation and tool does compile-time
dependency injection.

## Getting Started
FX-DJ requires python interpreter to be installed on machine.  
See [FX_METADATA Specification](https://github.com/Eremex/metadata_spec)
to learn configuration syntax.  
The project provides examples directory, use it first to become
familliar with tool.

## License
See the [LICENSE.txt](LICENSE.txt) file for details
