//
// Include definitions of itself.
//
#include FX_INTERFACE(WORLD)

//
// Metadata string marking this module as implementation of WORLD interface
// defined in world.h.
// Macro FX_METADATA will be defined as empty macro at compilation 
// phase, so, metadata is not visible to the compiler.
//
FX_METADATA(({ implementation: [WORLD, VERSION1] }))

//
// Implementation of interface function.
// It fills object with pointer to string and size of that string.
//
unsigned world_init_string(world_t* object)
{
  static char global_string[] = "world";
  unsigned error = 0;

  //
  // Initialize object if pointer is non-null.
  //
  if(object != NULL)
  {
    object->world_string = global_string;
    object->length = sizeof(global_string);
  }
  else
  {
    error = 1;
  }

  return error;
}

