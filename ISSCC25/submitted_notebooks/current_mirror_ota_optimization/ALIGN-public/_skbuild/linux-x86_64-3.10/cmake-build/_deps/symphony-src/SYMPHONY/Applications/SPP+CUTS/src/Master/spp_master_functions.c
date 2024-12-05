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
#include <stdio.h>
#include <stdlib.h>
#include <memory.h>
#include <string.h>

/* SYMPHONY include files */
#include "sym_timemeas.h"
#include "sym_macros.h"
#include "sym_constants.h"

/* SPP include files */
#include "spp.h"
#include "spp_common.h"
#include "spp_macros.h"
#include "spp_master_functions.h"

/*****************************************************************************/

void spp_read_params(spp_problem *spp, char *filename)
{
   char line[MAX_LINE_LENGTH], key[50], value[50];
   FILE *f;

   spp->lp_par = (spp_lp_params *) calloc(1, sizeof(spp_lp_params));
   spp->cg_par = (spp_cg_params *) calloc(1, sizeof(spp_cg_params));

   /* defaults for the parameters in spp_master */
   spp->par->dupc_at_loadtime = FALSE;
   spp->par->our_format_file_counter = -1;
   spp->par->matlab_format_file_counter = -1;
   spp->par->granularity  = 0;

   /* defaults for the parameters in spp_lp */
   spp->lp_par->do_lift_in_lp = 0;  /* false */
   spp->lp_par->lp_dj_threshold_frac = 0;
	spp->lp_par->lp_dj_threshold_abs = 0;   /* ==> threshold = lp_etol */
   spp->lp_par->lanmax = 30;
   spp->lp_par->which_atilde = 1;

   /* defaults for the parameters in spp_cg */
   spp->cg_par->min_violation_clique = .00001;
   spp->cg_par->min_violation_oddhole = .00001;
   spp->cg_par->min_violation_oddantihole = .00001;
   spp->cg_par->min_violation_wheel = .00001;
   spp->cg_par->min_violation_orthocut = .00001;
   spp->cg_par->min_violation_othercut = .00001;
   spp->cg_par->starcl_degree_threshold = 16;
   if (!strcmp(filename, ""))
      return;

   if ((f = fopen(filename, "r")) == NULL){
      printf("SYMPHONY: file %s can't be opened\n", filename);
      exit(1); /*error check for existence of parameter file*/
   }

   /* read in parameters from file */
   while ( fgets(line, MAX_LINE_LENGTH, f) != NULL ) {
      strcpy(key,"");
      sscanf(line, "%s%s", key, value);

      /* SPP Master params */
      
      if ( !strcmp(key, "input_file") || !strcmp(key, "infile") ) {
	 READ_STR_PAR(spp->par->infile);

      } else if ( !strcmp(key, "dupc_at_loadtime") ) {
	 READ_INT_PAR(spp->par->dupc_at_loadtime);
	 
      } else if ( !strcmp(key, "our_format_file") ) { 
	 READ_STR_PAR(spp->par->our_format_file);
	 
      } else if ( !strcmp(key, "our_format_file_counter") ) {
	 READ_INT_PAR(spp->par->our_format_file_counter);
	 
      } else if ( !strcmp(key, "matlab_format_file") ) { 
	 READ_STR_PAR(spp->par->matlab_format_file);

      } else if ( !strcmp(key, "matlab_format_file_counter") ) {
	 READ_INT_PAR(spp->par->matlab_format_file_counter);

      } else if ( !strcmp(key, "granularity") ) {
	 READ_DBL_PAR(spp->par->granularity);
	 
      /* SPP LP params */

      } else if ( !strcmp(key, "do_lift_in_lp") ) {
	 READ_INT_PAR(spp->lp_par->do_lift_in_lp);
	 
      } else if ( !strcmp(key, "lp_dj_threshold_frac") ) {
         READ_DBL_PAR(spp->lp_par->lp_dj_threshold_frac);

      } else if ( !strcmp(key, "lp_dj_threshold_abs") ) {
         READ_DBL_PAR(spp->lp_par->lp_dj_threshold_abs);

      } else if ( !strcmp(key, "lanmax") ) {
         READ_INT_PAR(spp->lp_par->lanmax);

      } else if ( !strcmp(key, "which_atilde") ) {
         READ_INT_PAR(spp->lp_par->which_atilde);

      /* SPP CG params */

      } else if ( !strcmp(key, "min_violation_clique") ) {
         READ_DBL_PAR(spp->cg_par->min_violation_clique);

      } else if ( !strcmp(key, "min_violation_oddhole") ) {
         READ_DBL_PAR(spp->cg_par->min_violation_oddhole);

      } else if ( !strcmp(key, "min_violation_oddantihole") ) {
         READ_DBL_PAR(spp->cg_par->min_violation_oddantihole);

      } else if ( !strcmp(key, "min_violation_wheel") ) {
         READ_DBL_PAR(spp->cg_par->min_violation_wheel);

      } else if ( !strcmp(key, "min_violation_orthocut") ) {
         READ_DBL_PAR(spp->cg_par->min_violation_orthocut);
      
      } else if ( !strcmp(key, "min_violation_othercut") ) {
	 READ_DBL_PAR(spp->cg_par->min_violation_othercut);
	 
      } else if ( !strcmp(key, "starcl_degree_threshold") ) {
	 READ_INT_PAR(spp->cg_par->starcl_degree_threshold);
	 
      } else if ( !strcmp(key, "starcl_which_node") ) {
         READ_INT_PAR(spp->cg_par->starcl_which_node);
	 
      } else if ( !strcmp(key, "rowcl_degree_threshold") ) {
	 READ_INT_PAR(spp->cg_par->rowcl_degree_threshold);
	 
      } else if ( !strcmp(key, "max_hub_num") ) {
         READ_INT_PAR(spp->cg_par->max_hub_num);
	 
      } else if ( !strcmp(key, "eval_oh_during_lifting") ) {
         READ_INT_PAR(spp->cg_par->eval_oh_during_lifting);
      }
   }
   
   /* set some parameters */
   spp->lp_par->granularity = spp->par->granularity;
   fclose(f);
}

/*****************************************************************************/

void spp_print_params(spp_problem *spp)
{
   spp_parameters *par = spp->par;

   printf("###########################################################\n");
   printf("Parameter settings:\n");
   printf("   infile: %s\n", par->infile);
   printf("   dupc_at_loadtime: %i\n", par->dupc_at_loadtime);
   printf("   our_format_file: %s\n", par->our_format_file);
   printf("   our_format_file_counter: %i\n",par->our_format_file_counter);
   printf("   matlab_format_file: %s\n", par->matlab_format_file);
   printf("   matlab_format_file_counter: %i\n",
	  par->matlab_format_file_counter);
   printf("   granularity: %f\n", par->granularity);
   printf("\n\n");
}

/*****************************************************************************/

/*===========================================================================*
 * The following routine reads in the data from the input file. The input    *
 * file has to be in the following format:                                   *
 *   First row of the input file:                                            *
 *        <t>   <m>   <n>   <nzcnt>                                          *
 *             where <t>: type of input file. (currently: OUR_FORMAT only)   *
 *                   <m>: # of rows in the matrix of the problem.            *
 *                        Rows are assumed to be numbered from 1 to m.       *
 *                   <n>: # of columns in the matrix of the problem.         *
 *                   <nzcnt>: # of nonzeros (=ones) in the matrix.           *
 *                                                                           *
 *  A general row of the input file describing a COLUMN of the matrix:       *
 *        <col_name_j>   <c_j>   <nzcnt_j>   <pos_1>  ...   <pos_nzcnt_j>    *
 *             where <col_name_j>: the name of the column (integer).         *
 *                   <c_j>: objective function coefficient. Integral in HP   *
 *                          problems, double in telebus problems.            *
 *                   <nzcnt_j>: number of nonzeros in this column.           *
 *                   <pos_1> ... : indices of rows where the nonzeros are.   *
 *                      Note that in the case of the set partitioning        *
 *                      problem, the matrix is 0-1.                          *
 *                                                                           *
 * our0 format: same as above but rows are numbered from 0 to rownum-1.
 *===========================================================================*/

void spp_read_input(spp_problem *spp)
{
   FILE *f;
   col_ordered *matrix;
   int deleted_cols;  /* number of columns deleted */
   int colnum;
   double T = 0;

   used_time(&T);
   
   if ((f = fopen(spp->par->infile, "r")) == NULL)
      OPEN_READ_ERROR(spp->par->infile);

   if(spp->par->verbosity > -1){
     printf("########################################################\n");
     printf("Reading input file %s...\n", spp->par->infile);
   }
   matrix = spp->cmatrix = (col_ordered *) calloc(1, sizeof(col_ordered));
   
   /* read in the type of the problem, rownum, colnum and nzcnt */
   if (fscanf(f, "%i", &spp->input_type) != 1) IO_ERROR;
   if (fscanf(f, "%i%i%i", &matrix->rownum, &matrix->colnum,
	      &matrix->nzcnt) != 3) IO_ERROR;
   colnum = matrix->colnum;
   printf("      input type: %i, rownum: %i, colnum: %i, nzcnt: %i\n",
	   spp->input_type, matrix->rownum, colnum, matrix->nzcnt);
   
   matrix->colnames = (int *) malloc(colnum * ISIZE);
   matrix->obj = (double *) malloc(colnum * DSIZE);
   matrix->matbeg = (int *) malloc((colnum+1) * ISIZE);
   matrix->matind = (row_ind_type *)
      malloc(matrix->nzcnt * sizeof(row_ind_type));

   switch (spp->input_type){
      
    case OUR_FORMAT:
      
      if ( spp->par->dupc_at_loadtime ) {
	 if ( (deleted_cols = read_our_del_dupl(matrix, f)) >= 0 ) {
	    printf("   Deleted %i columns at loadtime,\n",deleted_cols);
	    printf("      rownum: %i, colnum: %i, nzcnt: %i\n",
		   matrix->rownum, matrix->colnum, matrix->nzcnt);
	 }
      } else {
	 read_our_no_del(matrix, f); 
      }
      break;
      
    case OUR_FORMAT_0:
      
      if ( spp->par->dupc_at_loadtime ) {
	 if ( (deleted_cols = read_our0_del_dupl(matrix, f)) >= 0 ) {
	    printf("   Deleted %i columns at loadtime,\n",deleted_cols);
	    printf("      rownum: %i, colnum: %i, nzcnt: %i\n",
		   matrix->rownum, matrix->colnum, matrix->nzcnt);
	 }
      } else {
	 read_our0_no_del(matrix, f); 
      }
      break;

    default:
      IO_ERROR;
      
   } /* end switch */

   matrix->col_deleted = (char *) calloc(matrix->colnum/BITSPERBYTE +1, CSIZE);

   fclose(f);
   printf("\n\n");

   spp->stat[READ_INPUT].time += used_time(&T);
   spp->stat[READ_INPUT].freq++;
}

/*===========================================================================*
 * read our format, no deletion of duplicate columns at loadtime.
 *===========================================================================*/

void read_our_no_del(col_ordered *matrix, FILE *f)
{
   int colnum = matrix->colnum;
   int rownum = matrix->rownum;
   int *colnames = matrix->colnames;
   double *obj = matrix->obj;
   int *matbeg = matrix->matbeg;
   row_ind_type *matind = matrix->matind;

   int j;  /* runs thru columns */
   int i;  /* runs thru rows intersecting a column */
   int nz_count;  /* count nonzeros */
   int col_nzcnt;  /* number of nonzeros in a column */  
   int value;  /* a temporary variable */

   
   for ( j = 0, nz_count = 0, matbeg[0] = 0; j < colnum; j++ ) {

      /* read in the name of the column, obj fn coeff and
	 num of rows intersecting this column */
      if (fscanf(f, "%i%lf%i", &colnames[j], &obj[j], &col_nzcnt) != 3)
	 IO_ERROR;

      /* read in row indices */
      for ( i = 0; i < col_nzcnt; i++){
	 if (fscanf(f, "%i", &value) != 1)
	    IO_ERROR;
	 if ( !value || (value > rownum))
	    IO_ERROR;
	 matind[nz_count++] = value-1;
      }
      matbeg[j+1] = matbeg[j] + col_nzcnt;
   }
}
   
/*===========================================================================*
 * read our format, delete duplicate columns (that are next to
 * each other) at loadtime. returns the number of columns deleted, or
 * -1 in case of failure.
 *===========================================================================*/

int read_our_del_dupl(col_ordered *matrix, FILE *f)
{
   int colnum = matrix->colnum;
   int rownum = matrix->rownum;
   int *colnames = matrix->colnames;
   double *obj = matrix->obj;
   int *matbeg = matrix->matbeg;
   row_ind_type *matind = matrix->matind;
   
   int j;  /* runs thru columns */
   int i;  /* runs thru rows intersecting a column */
   int col_count, nz_count;  /* count columns and nonzeros */
   int col_nzcnt;  /* number of nonzeros in a column */  
   int value;  /* a temporary variable */
   int deleted_cols;  /* number of columns deleted */

   
   for ( j = 0, nz_count = 0, col_count = 0, deleted_cols = 0,
	matbeg[0] = 0; j < colnum; j++ ) {
      
      /* read in the name of the column, obj fn coeff and
	 num of rows intersecting this column */
      if (fscanf(f, "%i%lf%i",
		 &colnames[col_count], &obj[col_count], &col_nzcnt) != 3)
	 IO_ERROR;
      
      /* read in row indices */
      for ( i = 0; i < col_nzcnt; i++){
	 if (fscanf(f, "%i", &value) != 1)
	    IO_ERROR;
	 if ( !value || (value > rownum))
	    IO_ERROR;
	 matind[nz_count++] = value-1;
      }
      matbeg[col_count+1] = matbeg[col_count] + col_nzcnt;
      
      /* if this this and the previous column are of the same length */
      if ( col_count > 0 &&
	  matbeg[col_count] - matbeg[col_count-1] == col_nzcnt ) {
	 /* if the two columns ARE the same */
	 if (!memcmp( matind+matbeg[col_count-1], matind+matbeg[col_count],
		   col_nzcnt * sizeof(row_ind_type)) ) {
	    /* if new column has a better obj fn coeff then keep this;
	       no change in matind or matbeg since cols are same */
	    if ( obj[col_count] < obj[col_count-1] ) {
	       obj[col_count-1] = obj[col_count];
	       colnames[col_count-1] = colnames[col_count];
	    }
	    deleted_cols++;
	    nz_count -= col_nzcnt;
	 } else {
	    col_count++;
	 }
      } else {
	 col_count++;
      }
   }
   
   if ( deleted_cols ) {
      matrix->colnum = col_count;
      matrix->rownum = rownum;
      matrix->nzcnt = nz_count;
      matrix->colnames = (int *) realloc((char *)matrix->colnames,
					 col_count * ISIZE);
      matrix->obj = (double *) realloc((char *)matrix->obj,
				       col_count * DSIZE );
      matrix->matbeg = (int *) realloc((char *)matrix->matbeg,
				       (col_count+1) * ISIZE );
      matrix->matind = (row_ind_type *)
	 realloc((char *)matrix->matind, nz_count * sizeof(row_ind_type) );
   }
   return(deleted_cols);
}
   
/*===========================================================================*
 * read our0 format, no deletion of duplicate columns at loadtime.
 *===========================================================================*/

void read_our0_no_del(col_ordered *matrix, FILE *f)
{
   int colnum = matrix->colnum;
   int rownum = matrix->rownum;
   int *colnames = matrix->colnames;
   double *obj = matrix->obj;
   int *matbeg = matrix->matbeg;
   row_ind_type *matind = matrix->matind;

   int j;  /* runs thru columns */
   int i;  /* runs thru rows intersecting a column */
   int nz_count;  /* count nonzeros */
   int col_nzcnt;  /* number of nonzeros in a column */  
   int value;  /* a temporary variable */
   int rownum_minus_1 = rownum - 1;

   
   for ( j = 0, nz_count = 0, matbeg[0] = 0; j < colnum; j++ ) {

      /* read in the name of the column, obj fn coeff and
	 num of rows intersecting this column */
      if (fscanf(f, "%i%lf%i", &colnames[j], &obj[j], &col_nzcnt) != 3)
	 IO_ERROR;

      /* read in row indices */
      for ( i = 0; i < col_nzcnt; i++){
	 if (fscanf(f, "%i", &value) != 1)
	    IO_ERROR;
	 if ( value < 0 || value > rownum_minus_1 )
	    IO_ERROR;
	 matind[nz_count++] = value;
      }
      matbeg[j+1] = matbeg[j] + col_nzcnt;
   }
}

/*===========================================================================*
 * read our0 format, delete duplicate columns (that are next to
 * each other) at loadtime. returns the number of columns deleted, or
 * -1 in case of failure.
 *===========================================================================*/

int read_our0_del_dupl(col_ordered *matrix, FILE *f)
{
   int colnum = matrix->colnum;
   int rownum = matrix->rownum;
   int *colnames = matrix->colnames;
   double *obj = matrix->obj;
   int *matbeg = matrix->matbeg;
   row_ind_type *matind = matrix->matind;
   int rownum_minus_1 = rownum - 1;
   
   int j;  /* runs thru columns */
   int i;  /* runs thru rows intersecting a column */
   int col_count, nz_count;  /* count columns and nonzeros */
   int col_nzcnt;  /* number of nonzeros in a column */  
   int value;  /* a temporary variable */
   int deleted_cols;  /* number of columns deleted */

   
   for ( j = 0, nz_count = 0, col_count = 0, deleted_cols = 0,
	matbeg[0] = 0; j < colnum; j++ ) {
      
      /* read in the name of the column, obj fn coeff and
	 num of rows intersecting this column */
      if (fscanf(f, "%i%lf%i",
		 &colnames[col_count], &obj[col_count], &col_nzcnt) != 3)
	 IO_ERROR;
      
      /* read in row indices */
      for ( i = 0; i < col_nzcnt; i++){
	 if (fscanf(f, "%i", &value) != 1)
	    IO_ERROR;
	 if ( value < 0 || value > rownum_minus_1)
	    IO_ERROR;
	 matind[nz_count++] = value;
      }
      matbeg[col_count+1] = matbeg[col_count] + col_nzcnt;
      
      /* if this this and the previous column are of the same length */
      if ( col_count > 0 &&
	  matbeg[col_count] - matbeg[col_count-1] == col_nzcnt ) {
	 /* if the two columns ARE the same */
	 if (!memcmp( matind+matbeg[col_count-1], matind+matbeg[col_count],
		   col_nzcnt * sizeof(row_ind_type)) ) {
	    /* if new column has a better obj fn coeff then keep this;
	       no change in matind or matbeg since cols are same */
	    if ( obj[col_count] < obj[col_count-1] ) {
	       obj[col_count-1] = obj[col_count];
	       colnames[col_count-1] = colnames[col_count];
	    }
	    deleted_cols++;
	    nz_count -= col_nzcnt;
	 } else {
	    col_count++;
	 }
      } else {
	 col_count++;
      }
   }
   
   if ( deleted_cols ) {
      matrix->colnum = col_count;
      matrix->rownum = rownum;
      matrix->nzcnt = nz_count;
      matrix->colnames = (int *) realloc((char *)matrix->colnames,
					 col_count * ISIZE);
      matrix->obj = (double *) realloc((char *)matrix->obj,
				       col_count * DSIZE );
      matrix->matbeg = (int *) realloc((char *)matrix->matbeg,
				       (col_count+1) * ISIZE );
      matrix->matind = (row_ind_type *)
	 realloc((char *)matrix->matind, nz_count * sizeof(row_ind_type) );
   }
   return(deleted_cols);
}

/*****************************************************************************/

void spp_fix_lex(spp_problem *spp)
{
   int *order;    /* order is allocated in lexsort() */
   col_ordered *matrix = spp->cmatrix;
   int colnum = matrix->colnum;
   int *colnames = matrix->colnames;
   double *obj = matrix->obj;
   int *matbeg = matrix->matbeg;
   row_ind_type *matind = matrix->matind;

   int *new_colnames = (int *) malloc(colnum * ISIZE);
   double *new_obj = (double *) malloc( colnum * DSIZE);
   int *new_matbeg = (int *) malloc((colnum+1) * ISIZE);
   row_ind_type *new_matind = (row_ind_type *)
      malloc( matrix->nzcnt * sizeof(row_ind_type));

   int i, col, col_length;

   /* order is a permutation of column indices that shows their lex order */
   order = spp_lexsort(matrix);

   /* copy the columns into the new data structure */
   for ( i = 0, new_matbeg[0] = 0; i < colnum; i++) {
      col = order[i];
      new_colnames[i] = colnames[col];
      new_obj[i] = obj[col];
      col_length = matbeg[col+1] - matbeg[col];
      memcpy((char *)(new_matind + new_matbeg[i]),
	     (char *)(matind + matbeg[col]),
	     col_length * sizeof(row_ind_type) );
      new_matbeg[i+1] = new_matbeg[i] + col_length;
   }

   FREE(colnames);
   FREE(obj);
   FREE(matbeg);
   FREE(matind);

   matrix->colnames = new_colnames;
   matrix->obj = new_obj;
   matrix->matbeg = new_matbeg;
   matrix->matind = new_matind;

   FREE(order);
}


/*****************************************************************************/

/*===========================================================================*
 * Write the column ordered matrix into a file (or stdout), in our format.
 * counter is increased here.
 *===========================================================================*/

void spp_matrix_to_our(col_ordered *matrix, char *filename, int *counter)
{
   char fname[MAX_FILE_NAME_LENGTH];
   FILE *f;
   
   int i;  /* runs thru columns */
   int colnum = matrix->colnum;
   int *colnames = matrix->colnames;
   double *obj = matrix->obj;
   int *matbeg = matrix->matbeg;
   row_ind_type *matind = matrix->matind;
   int col_nzcnt;  /* number of rows intersecting a column */
   int j;  /* runs thru rows intersecting a column */
   row_ind_type *col_beg;  /* pointer to the beginning of a column in matind */

   f = get_filehandler(*counter, filename, fname);
   (*counter)++;
   
   /* first row: type, rownum, colnum, nzcnt */
   fprintf(f, "%8i %8i %15i %15i\n", OUR_FORMAT_0, matrix->rownum,
	   colnum, matrix->nzcnt);
   
   /* for each column: colname, obj, col_nzcnt, row indices */
   for ( i = 0; i < colnum; i++ ) {
      col_nzcnt = matbeg[i+1]-matbeg[i];
      col_beg = matind + matbeg[i];
      fprintf(f, "%8i%9.2f%3i ", colnames[i], obj[i], col_nzcnt);
      for ( j = 0; j < col_nzcnt; j++ )
	 fprintf(f, " %4i", col_beg[j]);
      fprintf(f, "\n");
   }
   
   if ( f != stdout )
      fclose(f);

   printf("########################################################\n");
   printf("Saved problem matrix into file %s\n\n\n", fname);
}

/*****************************************************************************/

/*===========================================================================*
 * Write the column ordered matrix into a file (or stdout), in flat (matlab
 * readable) format. (note that vectors indices start from 1 in matlab)
 * counter is increased here.
 *===========================================================================*/

void spp_matrix_to_matlab(col_ordered *matrix, char *filename, int *counter)
{
   char fname[MAX_FILE_NAME_LENGTH];
   FILE *f;
   
   int i;  /* runs thru columns */
   int colnum = matrix->colnum;
   int col_nzcnt;  /* number of rows intersecting a column */
   int *matbeg = matrix->matbeg;
   row_ind_type *matind = matrix->matind;
   int j;  /* runs thru rows intersecting a column */
   row_ind_type *col_beg;  /* pointer to the beginning of a column in matind */
   
   f = get_filehandler(*counter, filename, fname);
   (*counter)++;
      
   /* first print out "rownum colnum 0" */
   fprintf(f, "%10i %10i %10i\n", matrix->rownum, colnum, 0);

   /* for each column, and for each row intersecting this column
      print "row_index column_index 1" */
   for ( i = 0; i < colnum; i++ ) {
      col_nzcnt = matbeg[i+1] - matbeg[i];
      col_beg = matind + matbeg[i];
      for ( j = 0; j < col_nzcnt; j++ ) {
	 fprintf(f, "%10i %10i %10i\n", col_beg[j]+1, i+1, 1);
      }
   }
      
   if ( f != stdout )
      fclose(f);
   
   printf("########################################################\n");
   printf("Saved problem matrix into file %s\n\n", fname);
}
