#ifndef _DECOMP_TYPES_H
#define _DECOMP_TYPES_H

#define COL_BLOCK_SIZE 10

typedef struct COL_DATA{
   int  size;    /*the size of the coef array*/
   char *coef;   /*an array which contains the data necessary to construct
		   the column -- it is stored in a packed form. */
   int  level;
   int  touches; /*the number of times (in a row) the column was checked
		   for violation and found not to be violated. This is
		   a measure of the usefulness of the column*/
}col_data;

typedef struct DCMP_COL_SET{
   double *lb;
   double *ub;
   double *obj;
   int *matbeg;
   int *matind;
   double *matval;
   int num_cols;
   int max_cols;
   int nzcnt;
   int max_nzcnt;
   int bd_type;
   int ubnd;
}dcmp_col_set;

#endif
