/* EasyHybrid4 CI: minimal <strings.h> for building pDynamo3 with MSVC. */
#ifndef EASYHYBRID_MSVC_STRINGS_H
#define EASYHYBRID_MSVC_STRINGS_H
#include <string.h>
#define strcasecmp  _stricmp
#define strncasecmp _strnicmp
#endif
