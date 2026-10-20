/* EasyHybrid4 CI: POSIX calls used by pDynamo3's bundled PRIMME on Windows.
   Force-included into the dcprimme library only (MSVC /FI, MinGW -include).

   gethostname(): neither MSVC nor MinGW declares it outside Winsock; PRIMME
   uses it only to print the machine name in diagnostics. The call is renamed
   so it cannot clash with a Winsock declaration.

   valloc(): page-aligned malloc, absent on Windows. PRIMME releases these
   work arrays with free(), so the replacement must be malloc() (not
   _aligned_malloc, whose memory free() cannot release); page alignment is
   only a performance hint and x64 malloc already aligns to 16 bytes. */
#ifndef EASYHYBRID_PRIMME_WINDOWS_H
#define EASYHYBRID_PRIMME_WINDOWS_H
#include <stddef.h>
#include <stdlib.h>
#define valloc( size ) malloc ( size )
__declspec(dllimport) int __stdcall GetComputerNameA(char *buffer, unsigned long *size);
/* POSIX signature, so a <unistd.h> that does declare gethostname() agrees. */
static __inline int easyhybrid_primme_gethostname(char *name, size_t length)
{
    unsigned long size = (unsigned long) length;
    return GetComputerNameA(name, &size) ? 0 : -1;
}
#define gethostname easyhybrid_primme_gethostname
#endif
