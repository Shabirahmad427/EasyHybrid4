/* EasyHybrid4 CI: minimal <sys/time.h> for building pDynamo3 with MSVC.
   Used only by PRIMME's wall-clock timers (cprimme/wtime.c). */
#ifndef EASYHYBRID_MSVC_SYS_TIME_H
#define EASYHYBRID_MSVC_SYS_TIME_H
#include <time.h>
#if !defined(_WINSOCK2API_) && !defined(_WINSOCKAPI_)
struct timeval { long tv_sec; long tv_usec; };
#endif
struct timezone { int tz_minuteswest; int tz_dsttime; };
static __inline int gettimeofday(struct timeval *tv, struct timezone *tz)
{
    struct timespec now;
    (void) tz;
    if (!timespec_get(&now, TIME_UTC)) return -1;
    tv->tv_sec  = (long) now.tv_sec;
    tv->tv_usec = (long) (now.tv_nsec / 1000);
    return 0;
}
#endif
