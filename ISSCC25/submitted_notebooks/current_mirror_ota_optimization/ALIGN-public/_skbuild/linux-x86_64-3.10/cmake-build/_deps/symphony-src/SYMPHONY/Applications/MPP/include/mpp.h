/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* the Mixed Postman Problem.                                                */
/*                                                                           */
/* (c) Copyright 2005-2008 Lehigh University. All Rights Reserved.           */
/*                                                                           */
/* This application was originally developed by Andrew Hofmann and was       */
/* modified by  Ted Ralphs (ted@lehigh.edu)                                  */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

#ifndef _MPP_H
#define _MPP_H

/* Cut types */

#define ODD_CUT 1

/*---------------------------------------------------------------------------*\
 * Use this data structure to store the value of any run-time parameters.
\*---------------------------------------------------------------------------*/

typedef struct MPP_PARAMETERS{
   /* Name of file containingthe instance data */
   char             infile[MAX_FILE_NAME_LENGTH + 1];
   int              test;
   char             test_dir[MAX_FILE_NAME_LENGTH +1]; /* Test files directory */  
}mpp_parameters;

/*---------------------------------------------------------------------------*\
 * Use this data structure to store the instance data after it is read in.
\*---------------------------------------------------------------------------*/

typedef struct MPP_PROBLEM{
   mpp_parameters  par;        /* the parameters */
   int             numnodes;   /* the number of nodes in the graph */
   int             numedges;   /* number of edges in the graph */
   int             numarcs;    /* number of arcs in the graph */
   int            *cost;       /* an array containing the costs */
   int            *head;       /* an array containing the head of each arc/edge*/
   int            *tail;       /* an array containing the tail of each arc/edge*/
   char           *type;      /* an array containing the variable types */
   int            *is_odd;     /* array containing a 1 if odd 0 if not*/
   int             odd_checker;/*indicates if odds have been checked */
}mpp_problem; 

#endif
