#ifndef _OUTPUT_
#define _OUTPUT_

//
// Ordinary includes (without FX_INTERFACE macro are not visible to the configurator).
//
#include <stdio.h>

//
// Some interface function.
//
void output_string(char* string);

//
// This module defines alternative implementation of module OUTPUT.
//
FX_METADATA(({ interface: [OUTPUT, CONSOLE] }))

#endif
