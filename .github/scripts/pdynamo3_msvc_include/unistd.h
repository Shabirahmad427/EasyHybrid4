/* EasyHybrid4 CI: minimal <unistd.h> for building pDynamo3 with MSVC.
   pDynamo3's bundled PRIMME uses it only for gethostname() in its
   diagnostic output. Declared here without <windows.h> and its macros. */
#ifndef EASYHYBRID_MSVC_UNISTD_H
#define EASYHYBRID_MSVC_UNISTD_H
#include <io.h>
#include <process.h>
__declspec(dllimport) int __stdcall GetComputerNameA(char *buffer, unsigned long *size);
static __inline int gethostname(char *name, int length)
{
    unsigned long size = (unsigned long) length;
    return GetComputerNameA(name, &size) ? 0 : -1;
}
#endif
