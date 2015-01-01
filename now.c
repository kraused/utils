
#define _XOPEN_SOURCE

#include <stdlib.h>
#include <stdio.h>
#include <time.h>
#include <sys/time.h>
#include <errno.h>

#define likely(X)       __builtin_expect(!!(X), 1)
#define unlikely(X)     __builtin_expect(!!(X), 0)


int main(int argc, char **argv)
{
	int            err;
	struct timeval tv;
	struct tm      tm;
	const char     *fmt;
	char           *buf;
	struct tm      *p;
	long long      sz, n;

	fmt = "%Y-%m-%d\n";
	if (argc > 1) {
		if (('-' == argv[1][0]) && 
		    ('f' == argv[1][1]) &&
		    ( 0  == argv[1][2]))
			fmt = "%Y-%m-%dT%H%M%SZ%z\n";
	}

	err = gettimeofday(&tv, NULL);
	if (unlikely(err)) {
		fprintf(stderr, "gettimeofday failed. errno = %d says '%s'.\n", 
		        errno, strerror(errno));
		return 1;
	}

	p = localtime_r(&tv.tv_sec, &tm);
	if (unlikely(!p)) {
		fprintf(stderr, "localtime_r returned NULL.\n");
		return 1;
	}

	sz  = 64;
	buf = malloc(sz);
	if (unlikely(!buf)) {
		fprintf(stderr, "malloc returned NULL.\n");
		return 1;
	}

	do 
	{
		n = strftime(buf, sz, fmt, &tm);
		if (0 == n) {
			sz *= 2;
			buf = realloc(buf, sz);
			if (unlikely(!buf)) {
				fprintf(stderr, "realloc returned NULL.\n");
				return 1;
			}
		}
	} while(0 == n);

	free(buf);

	return 0;
}

