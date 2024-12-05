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

#ifndef _SPP_H
#define _SPP_H

#include "sym_proto.h"

#include "spp_types.h"
#include "spp_constants.h"

/*---------------------------------------------------------------------------*\
 * Use this data structure to store the value of any run-time parameters.
\*---------------------------------------------------------------------------*/

/* infile  -- contains the problem matrix (in our format only right now)
   our_format_file  -- when the problem matrix is needed to be saved in
                       our format, a file name is generated from this
		       name and our_format_file_counter. If the counter
		       is negative, won't save the matrix anywhere.
   matlab_format_file  -- when the sparsity structure of the problem
                          matrix is interesting, it can be saved in this
			  format (a nzcnt+1 by 3 table that matlab reads in to
			  form a sparse matrix), see show_sparsity.m
			  The counter works the same way as above.

   dupc_at_loadtime -- if set, delete duplicate columns that are next to
                       each other when loading in the problem.

   granularity -- the minimum difference between the objective values of two
                  (integral) feasible solutions if the objective values are
		  not considered the same  minus  epsilon.
		  (e.g., if all objective coefficients are integers then
		  granularity is 1.00 - epsilon, say .999)                   */

typedef struct SPP_PARAMETERS{
   /* Name of file containing the instance data */
   char             infile[MAX_FILE_NAME_LENGTH + 1];

   int              dupc_at_loadtime;

   char             our_format_file[MAX_FILE_NAME_LENGTH];
   int              our_format_file_counter;

   char             matlab_format_file[MAX_FILE_NAME_LENGTH];
   int              matlab_format_file_counter;

   double           granularity;
   int              test;
   char             test_dir[MAX_FILE_NAME_LENGTH +1]; /* Test files directory */ 
   int              verbosity;
}spp_parameters;

/*---------------------------------------------------------------------------*\
 * Use this data structure to store the instance data after it is read in.
\*---------------------------------------------------------------------------*/

typedef struct SPP_PROBLEM{

   spp_parameters  *par;    /* Parameters */

   statistics      *stat;            /* statistics */

   int              input_type;       /* the type of the problem instance */

   int              feasibility;      /* feasibility status of the problem */
   double           feas_value;       /* obj value of so far best feas soln */
   int              feas_sol_length;  /* number of vars in ... */
   int             *feas_sol;         /* names of vars in ... */

   int              orig_colnum;
   int              orig_rownum;
   int             *orig_names;
   double          *orig_obj;

   col_ordered     *cmatrix;          /* problem matrix (col ordered) */

}spp_problem;

#endif
