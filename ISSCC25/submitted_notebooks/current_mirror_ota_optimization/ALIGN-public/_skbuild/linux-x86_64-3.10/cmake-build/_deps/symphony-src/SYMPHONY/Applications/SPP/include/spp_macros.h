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

#ifndef _SPP_MACROS_H_
#define _SPP_MACROS_H_

#define OPEN_WRITE_ERROR(x) \
{ \
     (void) fprintf(stderr, \
		    "ERROR: Could not open file %s for writing!\n", x ); \
     exit(1); \
}
     
#define OPEN_READ_ERROR(x) \
{ \
     (void) fprintf(stderr, \
		    "ERROR: Could not open file %s for reading!\n", x ); \
     exit(1); \
}

#define IO_ERROR \
{ \
     (void) fprintf(stderr, \
		    "pp_read_input : Problem while reading input file\n"); \
     exit(1); \
}

#endif
