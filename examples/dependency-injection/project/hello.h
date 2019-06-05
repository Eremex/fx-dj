#ifndef _HELLO_
#define _HELLO_

//
// Ordinary includes (without FX_INTERFACE macro are not visible to the configurator).
//
#include <windows.h>
#undef interface

//
// Some data type defined by this module.
//
typedef struct _hello_t
{
  char* hello_string;
  unsigned int length;
}
hello_t;

//
// Some interface function...
//
unsigned hello_init_string(hello_t* object);

//
// ... and macro.
//
#define hello_object_as_string(hello_obj) ((hello_obj)->hello_string)

//
// Metadata string. Macro FX_METADATA will be defined as empty macro at compilation 
// phase, so, metadata is not visible to the compiler.
// This file is now associated with interface HELLO, second part of definition
// is implementation name (VERSION1).
//
FX_METADATA(({ interface: [HELLO, VERSION1] }))

#endif
