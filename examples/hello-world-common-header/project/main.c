//
// Include both modules.
//
#include FX_INTERFACE(HELLO)
#include FX_INTERFACE(WORLD)

//
// Ordinary includes are not visible to the configurator.
// These includes should be used for standard library.
// User is responsible for proper definitions of include search paths.
// 
#include <stdio.h>

//
// Metadata string. This module should be set as root module in configurator
// command line.
//
FX_METADATA(({ implementation: [MAIN, VERSION1] }))

//
// Application entry point.
//
int main(void)
{
  //
  // Using of external modules.
  //
  hello_t hello_object;
  world_t world_object;

  char buffer[50];
  char* buf_ptr = buffer;

  //
  // Init external objects.
  //
  hello_init_string(&hello_object);
  world_init_string(&world_object);

  memset(buffer, 0, sizeof(buffer));

  //
  // Copy string from first module into buffer.
  //
  strcpy_s(buf_ptr, hello_object.length, hello_object_as_string(&hello_object));

  //
  // Insert whitespace between words.
  //
  buf_ptr += strlen(buf_ptr);
  *buf_ptr++ = ' ';

  //
  // Copy second string to the buffer.
  //
  strcpy_s(buf_ptr, world_object.length, world_object_as_string(&world_object));

  //
  // Print the string.
  //
  printf(buffer);

  return 0;
}
