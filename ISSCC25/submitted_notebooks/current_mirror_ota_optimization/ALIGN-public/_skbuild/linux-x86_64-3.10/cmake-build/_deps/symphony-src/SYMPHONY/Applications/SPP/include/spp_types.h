/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* the Set Partitioning Problem.                                             */
/*                                                                           */
/* (c) Copyright 2005-2013 Marta Eso and Ted Ralphs. All Rights Reserved.    */
/*                                                                           */
/* This application was originally developed by Marta Eso and was modified   */
/* Ted Ralphs (ted@lehigh.edu)                                               */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

#ifndef _SPP_TYPES_H_
#define _SPP_TYPES_H_

#define    row_ind_type    short

typedef struct STATISTICS {
   int     freq;          /* how many times the routine was invoked */
   double  time;          /* how much time was spent in this routine */
}statistics;


typedef struct COL_ORDERED {
   int                colnum;        /* number of columns when this column
					ordered matrix was created */
   int                rownum;        /* same for number of rows */
   int                active_colnum; /* number of cols not marked for del */
   int                nzcnt;         /* number of nonzeros in the matrix */
   int               *colnames;
   char              *col_deleted;   /* a sequence of bits indicating which
					columns are deleted */
   double            *obj;           /* obj function coeffs */
   int               *matbeg;        /* pos of beginning of cols in matind */
   row_ind_type      *matind;        /* indices of rows listed for each col */
}col_ordered;


typedef struct ROW_ORDERED {
   int                rownum;        /* number of rows when this row ordered
					matrix was created. */
   int                colnum;        /* same for cols */
   int                active_rownum; /* number of rows not marked for del */
   int                nzcnt;         /* nonzero_count */
   int               *rownames;
   char              *row_deleted;   /* delete bits */
   int               *rmatbeg;       /* pos of beginning of rows in rmatind */
   int               *rmatind;       /* indices of cols listed for each row */
}row_ordered;

 
/* define bit manipulating macros. (a,i): starting at the memory location
   where a points to, find bit i; the order of bits is the following:
   7 6 5 4 3 2 1 0 15 14 13 12 11 10 9 8 23 22 ...
   setbit sets this bit to 1; clrbit clears this bit; isset returns 0 (false)
   if the bit is not set, and non-zero if it is set; isclr returns 1 (true)
   if the bit is not set and 0 (false) if the bit is set. */
#ifndef setbit
#define	setbit(a,i)	((a)[(i)/BITSPERBYTE] |= 1<<((i)%BITSPERBYTE))
#define	clrbit(a,i)	((a)[(i)/BITSPERBYTE] &= ~(1<<((i)%BITSPERBYTE)))
#define	isset(a,i)	((a)[(i)/BITSPERBYTE] & (1<<((i)%BITSPERBYTE)))
#define	isclr(a,i)	(((a)[(i)/BITSPERBYTE] & (1<<((i)%BITSPERBYTE))) == 0)
#endif


#endif
