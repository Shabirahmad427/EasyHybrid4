/* EasyHybrid4 CI: gethostname() for pDynamo3's bundled PRIMME on Windows.
   Force-included into the dcprimme library only (MSVC /FI, MinGW -include).
   Neither MSVC nor MinGW declares gethostname() outside Winsock; PRIMME
   uses it only to print the machine name in diagnostics. The call is
   renamed so it cannot clash with a Winsock declaration. */
#ifndef EASYHYBRID_PRIMME_GETHOSTNAME_H
#define EASYHYBRID_PRIMME_GETHOSTNAME_H
#include <stddef.h>
__declspec(dllimport) int __stdcall GetComputerNameA(char *buffer, unsigned long *size);
/* POSIX signature, so a <unistd.h> that does declare gethostname() agrees. */
static __inline int easyhybrid_primme_gethostname(char *name, size_t length)
{
    unsigned long size = (unsigned long) length;
    return GetComputerNameA(name, &size) ? 0 : -1;
}
#define gethostname easyhybrid_primme_gethostname
#endif
