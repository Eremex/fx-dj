#ifndef _WORLD_
#define _WORLD_

//
// Ordinary includes (without FX_INTERFACE macro are not visible to the configurator).
//
#include <windows.h>
#undef interface
//
// Some data type defined by this module.
//
typedef struct _world_t
{
  char* world_string;
  unsigned int length;
}
world_t;

//
// Some interface function...
//
unsigned world_init_string(world_t* object);

//
// ... and macro.
//
#define world_object_as_string(world_obj) ((world_obj)->world_string)

//
// Metadata string. Macro FX_METADATA will be defined as empty macro at compilation 
// phase, so, metadata is not visible to the compiler.
// This file is now associated with interface WORLD, second part of definition
// is implementation name (VERSION1).
//
FX_METADATA(({ interface: [WORLD, VERSION1] }))

#endif
