//
// Include definitions of itself.
//
#include FX_INTERFACE(OUTPUT)

//
// Metadata string marking this module as implementation of OUTPUT interface
// defined in output2.h.
// Macro FX_METADATA will be defined as empty macro at compilation 
// phase, so, metadata is not visible to the compiler.
//
FX_METADATA(({ implementation: [OUTPUT, CONSOLE] }))

//
// Implementation of interface function.
//
void output_string(char* string)
{
  //
  // Output message to console.
  //
  printf(string);
}
