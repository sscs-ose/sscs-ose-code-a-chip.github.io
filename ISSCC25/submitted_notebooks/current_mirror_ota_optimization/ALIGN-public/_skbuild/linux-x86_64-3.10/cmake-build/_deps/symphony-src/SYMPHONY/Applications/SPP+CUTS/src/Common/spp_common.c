/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* the Set Partitioning Problem.                                             */
/*                                                                           */
/* (c) Copyright 2005-2007 Marta Eso and Ted Ralphs. All Rights Reserved.    */
/*                                                                           */
/* This application was originally developed by Marta Eso and was modified   */
/* Ted Ralphs (ted@lehigh.edu)                                               */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

/* system include files */
#include <stdlib.h>
#include <string.h>

/* SYMPHONY include files */
#include "sym_constants.h"
#include "sym_macros.h"

/* SPP include files */
#include "spp_constants.h"
#include "spp_types.h"
#include "spp_common.h"
#include "spp_macros.h"

/*===========================================================================*/

static col_ordered *lexsort_matrix;
static row_ind_type *lexbeg_i, *lexbeg_j;
static int lexlength_i, lexlength_j;
static double obj_i, obj_j;

/*===========================================================================*/

int *spp_lexsort(col_ordered *matrix)
{
   int *order = (int *) malloc( matrix->colnum * ISIZE );

   int i;

   for ( i = matrix->colnum -1; i >= 0; i-- )
      order[i] = i;

   lexsort_matrix = matrix;

   qsort(order, matrix->colnum, ISIZE, spp_lexcompare);

   return(order);

}

/*****************************************************************************
 * qsort sorts into ascending (<) order. 
 * Return 1 if first elt is greater than second, -1 if less, 0 if equal.
 *****************************************************************************/

int spp_lexcompare(const void *i, const void *j)
{
   int k, l;  /* run thru the columns indexed by i and j */
   int *matbeg = lexsort_matrix->matbeg;
   
   lexbeg_i = lexsort_matrix->matind + matbeg[*(int *)i];
   lexbeg_j = lexsort_matrix->matind + matbeg[*(int *)j];
   lexlength_i = matbeg[*(int *)i+1] - matbeg[*(int *)i];
   lexlength_j = matbeg[*(int *)j+1] - matbeg[*(int *)j];
   obj_i = lexsort_matrix->obj[*(int *)i];
   obj_j = lexsort_matrix->obj[*(int *)j];

   for ( k = 0, l = 0; k < lexlength_i && l < lexlength_j; k++, l++) {
      if (lexbeg_i[k] < lexbeg_j[l]) {
	 return 1;
      } else if (lexbeg_i[k] > lexbeg_j[l]) {
	 return -1;
      }
   }

   if (k < lexlength_i)
      return 1;
   if (l < lexlength_j)
      return -1;

   /* now the two columns are the same. the one with the higher objective
      coef is the greater */
   if ( obj_i > obj_j ) {
      return 1;
   } else if ( obj_i < obj_j ) {
      return -1;
   }
   
   return 0;
}

/*===========================================================================*/

void spp_free_cmatrix(col_ordered *m)
{
   if ( m != NULL ) {
      FREE(m->colnames);
      FREE(m->col_deleted);
      FREE(m->obj);
      FREE(m->matbeg);
      FREE(m->matind);
   }
}

/*===========================================================================*/

void spp_free_rmatrix(row_ordered *m)
{
   if ( m != NULL ) {
      FREE(m->rownames);
      FREE(m->row_deleted);
      FREE(m->rmatbeg);
      FREE(m->rmatind);
   }
}

/*===========================================================================*/

/*****************************************************************************
 * Transform a column ordered matrix into a row ordered matrix.
 * Space must be already allocated for rmatbeg and rmatind. Fill out only
 * rmatbeg and rmatind in rmatrix.
 * i_tmpm and istar_tmpm temporary arrays of length at least m (allocated
 * before functio is invoked).
 *****************************************************************************/

void spp_column_to_row(col_ordered *cm, row_ordered *rm, int *i_tmpm,
		       int **istar_tmpm)
{
   int rownum = cm->rownum;
   int colnum = cm->colnum;
   int *rmatbeg = rm->rmatbeg;
   int *rmatind = rm->rmatind;
   int *matbeg = cm->matbeg;
   row_ind_type *matind = cm->matind;
   int *row_length = i_tmpm;
   int **row_pointers = istar_tmpm;

   row_ind_type *col_beg;
   int col_length;
   int i, j;

   /* zero out the row_length array */
   for ( i = rownum-1; i >= 0; i-- )
      row_length[i] = 0;

   /* for each row count how many columns intersect it */
   for ( i = cm->nzcnt - 1; i >= 0; i-- )
      row_length[matind[i]]++;

   /* now set rmatbeg appropriately, and set a pointer to the beginning of
      each row in rmatind */
   for ( i = 0, rmatbeg[0] = 0; i < rownum; i++ ) {
      rmatbeg[i+1] = rmatbeg[i] + row_length[i];
      row_pointers[i] = rmatind + rmatbeg[i];
   }
   
   /* construct rmatind: scan thru each column */
   for ( i = 0; i < colnum; i++ ) {
      col_length = matbeg[i+1] - matbeg[i];
      col_beg = matind + matbeg[i];
      for ( j = 0; j < col_length; j++ ) {
	 *row_pointers[col_beg[j]] = i;
	 row_pointers[col_beg[j]]++;
      }
   }
}

/*===========================================================================*/

/*****************************************************************************
 * Transform a row ordered matrix into a column ordered matrix.
 * Space must be already allocated for matbeg and matind. Fill out only
 * matbeg and matind in cmatrix.
 * i_tmpn and rowindstar_tmpn are tmp arrays allocated before this function
 * is invoked.
 *****************************************************************************/

void spp_row_to_column(row_ordered *rm, col_ordered *cm, int *i_tmpn,
		       row_ind_type **rowindstar_tmpn)
{
   int rownum = cm->rownum;
   int colnum = cm->colnum;
   int *rmatbeg = rm->rmatbeg;
   int *rmatind = rm->rmatind;
   int *matbeg = cm->matbeg;
   row_ind_type *matind = cm->matind;
   int *col_length = i_tmpn;
   row_ind_type **col_pointers = rowindstar_tmpn;

   int *row_beg;
   int row_length;
   int i, j;

   /* zero out the col_length array */
   for ( i = colnum-1; i >= 0; i-- )
      col_length[i] = 0;

   /* for each column count how many rows intersect it */
   for ( i = rm->nzcnt - 1; i >= 0; i-- )
      col_length[rmatind[i]]++;
   
   /* set matbeg appropriately and set the column-pointers */
   for ( i = 0, matbeg[0] = 0; i < colnum; i++ ) {
      matbeg[i+1] = matbeg[i] + col_length[i];
      col_pointers[i] = matind + matbeg[i];
   }
   
   /* construct matind: scan thru each row */
   for ( i = 0; i < rownum; i++ ) {
      row_length = rmatbeg[i+1] - rmatbeg[i];
      row_beg = rmatind + rmatbeg[i];
      for ( j = 0; j < row_length; j++ ) {
	 *col_pointers[row_beg[j]] = i;
	 col_pointers[row_beg[j]]++;
      }
   }
}

/*===========================================================================*/

/*===========================================================================*
 * Creates a file name using filename and counter (e.g. if filename is
 * "aaa.res" and counter is 4, fname will be "aaa_4.res", a handler to
 * the open file will be returned.
 *===========================================================================*/

FILE *get_filehandler(int counter, char *filename, char *fname)
{
   FILE *f;
   char *dot_pos;

   if ( filename[0] == 0 ) {
      fprintf(stderr, "ERROR: No filename is given!\n");
      exit(1);
   }
   if ( !strcmp(filename, (char *)"stdout") ) {
      f = stdout;
   } else {
      /* find the last "dot" in filename */
      if ( (dot_pos = strrchr(filename,'.')) == NULL ) {
	 sprintf(fname, "%s_%i", filename, counter);
      } else {
	 *dot_pos = 0;
	 sprintf(fname, "%s_%i.%s", filename, counter, dot_pos+1);
	 *dot_pos = '.';
      }
      if ((f = fopen(fname, "w")) == NULL) {
	 OPEN_WRITE_ERROR(fname);
	 exit(1);
      }     
   }

   return(f);
}
/*===========================================================================*/

void spp_reverse_char_string(int len, char *string)
{
   char tmp;
   int i;
   for (i = (len>>1) - 1; i >= 0; i--) {
      tmp = string[i];
      string[i] = string[len-i-1];
      string[len-i-1] = tmp;
   }
}

/*===========================================================================*/

void spp_reverse_int_string(int len, int *string)
{
   int tmp;
   int i;
   for (i = (len>>1) - 1; i >= 0; i--) {
      tmp = string[i];
      string[i] = string[len-i-1];
      string[len-i-1] = tmp;
   }
}

/*===========================================================================*/

void spp_reverse_double_string(int len, double *string)
{
   double tmp;
   int i;
   for (i = (len>>1) - 1; i >= 0; i--) {
      tmp = string[i];
      string[i] = string[len-i-1];
      string[len-i-1] = tmp;
   }
}

/*===========================================================================*/

/*****************************************************************************
 * Return TRUE if the two columns are orthogonal, FALSE if not.
 *****************************************************************************/

int spp_is_orthogonal(col_ordered *cmatrix, int col1, int col2)
{
   int *matbeg = cmatrix->matbeg;
   row_ind_type *matind = cmatrix->matind;

   int i, j;  /* i runs thru col1, j thru col2 */
   row_ind_type *col1_beg, *col2_beg;  /* pointers to the beginning of columns
					  col1 and col2 in the matind array */
   int is_orthogonal = TRUE;  /* assume columns are orthogonal */ 

   col1_beg = matind + matbeg[col1];
   col2_beg = matind + matbeg[col2];
   
   for ( i = matbeg[col1+1] - matbeg[col1] - 1,
	j = matbeg[col2+1] - matbeg[col2] - 1; i >= 0 && j >= 0;   ) {
      if ( col1_beg[i] < col2_beg[j] ) {
	 j--;
      } else if ( col1_beg[i] > col2_beg[j] ) {
	 i--;
      } else {
	 is_orthogonal = FALSE;
	 break;
      }
   }

   return(is_orthogonal);
}
