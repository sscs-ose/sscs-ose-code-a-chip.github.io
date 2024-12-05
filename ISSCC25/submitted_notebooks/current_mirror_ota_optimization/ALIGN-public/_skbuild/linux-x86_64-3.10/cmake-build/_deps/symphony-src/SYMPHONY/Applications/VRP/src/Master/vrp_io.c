/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* the Vehicle Routing Problem and the Traveling Salesman Problem.           */
/*                                                                           */
/* (c) Copyright 2000-2007 Ted Ralphs. All Rights Reserved.                  */
/*                                                                           */
/* This application was developed by Ted Ralphs (ted@lehigh.edu)             */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

/* system include files */
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>

/* SYMPHONY include files */
#include "sym_macros.h"
#include "sym_types.h"
#include "sym_master_u.h"
#include "sym_lp_params.h"

/* VRP include files */
#include "vrp_io.h"
#include "vrp_types.h"
#include "vrp_const.h"
#include "vrp_macros.h"
#include "compute_cost.h"
#include "small_graph.h"

/*===========================================================================*/

/*===========================================================================*\
 * This file contains the user I/O functions for the master process.
\*===========================================================================*/

/*===========================================================================*\
 * This first function reads in the data instance.
\*===========================================================================*/

void vrp_io(vrp_problem *vrp, char *infile)
{
  static char keywords[KEY_NUM][22] = {
    "NAME", 
    "NAME:",                 /* This section lists the names of the */
    "TYPE",                  /* possible fields in the data file    */
    "TYPE:",
    "COMMENT",
    "COMMENT:",
    "DIMENSION",
    "DIMENSION:",
    "CAPACITY",
    "CAPACITY:",
    "EDGE_WEIGHT_TYPE",
    "EDGE_WEIGHT_TYPE:",
    "EDGE_WEIGHT_FORMAT", 
    "EDGE_WEIGHT_FORMAT:", 
    "DISPLAY_DATA_TYPE",
    "DISPLAY_DATA_TYPE:",
    "EDGE_WEIGHT_SECTION", 
    "EDGE_WEIGHT_SECTION:", 
    "DISPLAY_DATA_SECTION", 
    "DISPLAY_DATA_SECTION:",
    "NODE_COORD_SECTION",
    "NODE_COORD_SECTION:",
    "NODE_COORD_TYPE",
    "NODE_COORD_TYPE:",
    "DEPOT_SECTION",
    "DEPOT_SECTION:",
    "CAPACITY_VOL",
    "CAPACITY_VOL:",
    "DEMAND_SECTION",
    "DEMAND_SECTION:",
    "TIME_WINDOW_SECTION",
    "TIME_WINDOW_SECTION:",
    "STANDTIME_SECTION",
    "STANDTIME_SECTION:",
    "PICKUP_SECTION",
    "PICKUP_SECTION:",
    "EOF",
    "EOF.",
    "NUMBER_OF_TRUCKS",
    "NUMBER_OF_TRUCKS:",
    "",
    "",
    "NO_MORE_TYPE"
  };

#define NCTYPE_NUM 3

  static char nctypes[NCTYPE_NUM][14] = {
    "TWOD_COORDS",
    "THREED_COORDS",     /*This section lists the possible node*/
    "NO_COORDS"          /*coordinate data types               */
  };

#define WTYPE_NUM 10

  static char wtypes[WTYPE_NUM][9] = {
    "EXPLICIT",
    "EUC_2D",            /*This is a list of the possible data types for */
    "EUC_3D",            /*edge weights                                  */
    "MAX_2D",
    "MAX_3D",
    "MAN_2D",
    "MAN_3D",
    "CEIL_2D",
    "GEO",
    "ATT"
  };

#define WFORMAT_NUM 9

  static char wformats[WFORMAT_NUM][20] = {
    "UPPER_ROW",
    "LOWER_ROW",          /*This is a list of the possible formats that*/
    "UPPER_DIAG_ROW",     /*the edge weight matrix could be given in   */
    "LOWER_DIAG_ROW",     /*if it is given explicitly                  */
    "UPPER_COL",
    "LOWER_COL",
    "UPPER_DIAG_COL",
    "LOWER_DIAG_COL",
    "FULL_MATRIX"
  };

#define DTYPE_NUM 3

  static char dtypes[DTYPE_NUM][14] = {
    "COORD_DISPLAY",
    "TWOD_DISPLAY",     /*This is a list of the various display data*/
    "NO_DISPLAY"        /*types                                     */
  };

  char line[LENGTH], line1[LENGTH], key[30], tmp[80];
  int wformat=-1, dtype=-1, nctype=-1;
  double fdummy;
  int i, j = 0;
  int l, m, *coef2;
  FILE *f;
  int node;
  double deg, min, coord_x, coord_y, coord_z;
  double x, y;
  int capacity_vol = FALSE;
  int k;
  register int vertnum = 0;
  distances *dist = &vrp->dist;

  if (!strcmp(infile, "")){
     printf("\nVrp I/O: No problem data file specified\n\n");
     exit(1);
  }
  
  if ((f = fopen(infile, "r")) == NULL){
     fprintf(stderr, "Vrp I/O: file '%s' can't be opened\n", infile);
     exit(1);
  }
  
  /*This loop reads in the next line of the data file and compares it
    to the list of possible keywords to determine what data will follow.
    It then reads the data into the appropriate field and iterates */
  
  while(NULL != fgets( line1, LENGTH, f)){
     strcpy(key,"");
     sscanf(line1,"%s",key); /*read in next keyword*/
     
     for (k = 0; k < KEY_NUM; k++) /*which data field comes next?*/
	if (strcmp(keywords[k], key) == 0) break;
     
     if (k == KEY_NUM){
	continue;
	fprintf(stderr, "Unknown keyword! bye.\n");
	exit(1); /*error check for acceptable data field*/
     }
     
     k >>= 1; /* This is a bit shift operation that divides k by 2    */
              /* since in the list of keywords, there are two possible*/
              /* formats for the keyword                              */
    
     if (strchr(line1,':')){
	strcpy(line, strchr(line1, ':')+1);
     }
     
     switch (k){
	
      case 0: /* NAME */
	if (!sscanf(line, "%s", vrp->name))
	   fprintf(stderr, "\nVrp I/O: error reading NAME\n\n");
	printf("PROBLEM NAME: \t\t%s\n", vrp->name);
	break;
      case 1 : /*TYPE*/
	sscanf(line, "%s", tmp);
	if (strcmp("CVRP", tmp) != 0){
	   if (strcmp("TSP", tmp) == 0){
	      vrp->par.tsp_prob = TRUE;
/*__BEGIN_EXPERIMENTAL_SECTION__*/
	   }else if (strcmp("BPP", tmp) == 0){
	      vrp->par.bpp_prob = TRUE;
/*___END_EXPERIMENTAL_SECTION___*/
	   }else{
	      fprintf(stderr, "This is not a recognized file type!\n");
	      exit(1);
	   }
	}
	printf("TYPE: \t\t\t%s\n", tmp);
      case 2 : /*COMMENT*/
#if 0
	if (!strncpy(tmp, line, 80))
	   fprintf(stderr, "\nVrp I/O: error reading COMMENT\n\n");
	printf("DESCRIPTION: \t\t%s\n", tmp);
#endif
	break;
      case 3 : /* DIMENSION */
	if (!sscanf(line, "%i", &k)){
	   fprintf(stderr, "Vrp I/O: error reading DIMENSION\n\n");
	   exit(1);
	}
	vertnum = vrp->vertnum = (int) k;
	vrp->edgenum = (int) vertnum * (vertnum - 1)/2;
	printf("DIMENSION: \t\t%i\n", k);
	break;
      case 4 : /*CAPACITY*/
	if (!sscanf(line, "%i", &k)){
	   fprintf(stderr, "Vrp I/O: error reading CAPACITY\n\n");
	   exit(1);
	}
	vrp->capacity = (int) k;
	break;
      case 5 : /* EDGE_WEIGHT_TYPE */
	sscanf(line, "%s", tmp);
	for (dist->wtype = 0; dist->wtype < WTYPE_NUM; (dist->wtype)++)
	   if (strcmp(wtypes[dist->wtype], tmp) == 0) break;
	if (dist->wtype == WTYPE_NUM) {
	   fprintf(stderr, "Unknown weight type : %s !!!\n", tmp);
	   exit(1);
	}
	break;
      case 6 : /* EDGE_WEIGHT_FORMAT */
	sscanf(line, "%s", tmp);
	for (wformat = 0; wformat < WFORMAT_NUM; wformat++)
	   if (strcmp(wformats[wformat], tmp) == 0) break;
	if (wformat == WFORMAT_NUM) {
	   fprintf(stderr, "Unknown weight type : %s !!!\n", tmp);
	   exit(1);
	}
	break;
      case 7 : /* DISPLAY_DATA_TYPE */
	sscanf(line, "%s", tmp);
	for (dtype = 0; dtype < DTYPE_NUM; dtype++)
	   if (strcmp(dtypes[dtype], tmp) == 0) break;
	if (dtype == DTYPE_NUM) {
	   fprintf(stderr, "Unknown display type : %s !!!\n", tmp);
	   exit(1);
	}
	break;
      case 8: /* EDGE_WEIGHT_SECTION */
	/*------------------------break if not EXPLICIT -*/
	if (dist->wtype != _EXPLICIT) break; 
	dist->cost = (int *) malloc (vrp->edgenum*sizeof(int));
	switch (wformat){
	 case 1 : /* LOWER_ROW */
	 case 4 : /* UPPER_COL */
	 case 3 : /* LOWER_DIAG_ROW */
	 case 6 : /* UPPER_DIAG_COL */
	   for (i=0, coef2=dist->cost; i<vertnum; i++){
	      for (j=0; j<i; j++, coef2++){
		 if (!fscanf(f,"%lf", &fdummy)){
		    fprintf(stderr, "Not enough data -- DIMENSION or "
			    "EDGE_WEIGHT_TYPE declared wrong\n");
		    exit(1);
		 }
		 else *coef2 = (int) fdummy;
	      }
	      if ((wformat==3 || wformat==6) && 
		  !fscanf(f,"%lf", &fdummy)){
		 fprintf(stderr, "Not enough data -- DIMENSION or "
			 "EDGE_WEIGHT_TYPE declared wrong\n");
		 exit(1);
	      }
	   }
	   if (fscanf(f,"%lf", &fdummy)){
	      fprintf(stderr, "Too much data -- DIMENSION or "
		      "EDGE_WEIGHT_TYPE declared wrong\n");
	      exit(1);
	   }
	   break;
	 case 0 : /* UPPER_ROW */
	 case 5 : /* LOWER_COL */
	 case 2 : /* UPPER_DIAG_ROW */
	 case 7 : /* LOWER_DIAG_COL */
	   for (i=0, coef2=dist->cost; i<vertnum; i++){
	      if (wformat==2 || wformat==7) 
		 if (!fscanf(f,"%lf", &fdummy)){
		    fprintf(stderr, "Not enough data -- DIMENSION or "
			    "EDGE_WEIGHT_TYPE declared wrong");
		    exit(1);
		 }
	      for (j=i+1; j<vertnum; j++){
		 if (!fscanf(f,"%lf", &fdummy)){
		    fprintf(stderr, "Not enough data -- DIMENSION or "
			    "EDGE_WEIGHT_TYPE declared wrong");
		    exit(1);
		 }
		 else coef2[j*(j-1)/2+i] = (int) fdummy;
	      }
	   }
	   if (fscanf(f,"%lf", &fdummy)){
	      fprintf(stderr, "Too much data -- DIMENSION or "
		      "EDGE_WEIGHT_TYPE declared wrong\n");
	      exit(1);
	   }
	   break;
	 case 8 : /* FULL_MATRIX */
	   for (i=0, coef2=dist->cost; i<vertnum; i++){
	      for (j=0; j<=i; j++)
		 if(!fscanf(f,"%lf", &fdummy)){
		    fprintf(stderr, "Not enough data -- DIMENSION or "
			    "EDGE_WEIGHT_TYPE declared wrong");
		    exit(1);
		 }
	      for (j=i+1; j<vertnum; j++){
		 if(!fscanf(f,"%lf", &fdummy)){
		    fprintf(stderr, "Not enough data -- DIMENSION or "
			    "EDGE_WEIGHT_TYPE declared wrong");
		    exit(1);
		 }
		 coef2[j*(j-1)/2+i] = (int) fdummy;
	      }
	   }
	   if (fscanf(f,"%lf", &fdummy)){
	      fprintf(stderr, "Too much data -- DIMENSION or "
		      "EDGE_WEIGHT_TYPE declared wrong\n");
	      exit(1);
	   }
	   break;
	}
	break;
      case 9 : /* DISPLAY_DATA_SECTION */
	/*--------------------- break if NO_DISPLAY -*/
	if (dtype != 1){
	   fprintf(stderr, "DISPLAY_DATA_SECTION exists"
		   "but not TWOD_DISPLAY!\n");
	   exit(1);
	}
	/* posx, posy -*/
	vrp->posx = (int *) malloc (vertnum*sizeof(int));
	vrp->posy = (int *) malloc (vertnum*sizeof(int));
	for (i=0; i<vertnum; i++){
	   if ((k = fscanf(f,"%i%lf%lf", &node, &x, &y)) != 3){
	      fprintf(stderr, "\nVrp I/O: error reading DISPLAY_DATA\n");
	      break;
	   }
	   vrp->posx[node-1] = (int)(x + 0.5);
	   vrp->posy[node-1] = (int)(y + 0.5);
	}
	if (fscanf(f,"%lf", &fdummy)){
	   fprintf(stderr, "\nVrp I/O: too much display data\n");
	   break;
	}
	break;
      case 10 : /* NODE_COORD_SECTION */
	if (nctype == -1) nctype = 0;  /*if not given: TWOD_COORDS*/
	if (dtype == -1 && ((dist->wtype == _EUC_2D) || /*display type*/
			    (dist->wtype == _MAX_2D) ||  /*not defd yet*/
			    (dist->wtype == _MAN_2D)   ))/*&& can disp.*/
	   dtype = 0;                               /* COORD_DISPLAY */
	if (dtype == 0){
	   vrp->posx = (int *) malloc (vertnum*sizeof(int));
	   vrp->posy = (int *) malloc (vertnum*sizeof(int));
	}
	dist->coordx = (double *) malloc (vertnum*sizeof(double));
	dist->coordy = (double *) malloc (vertnum*sizeof(double));
	if (nctype == 1)
	   dist->coordz = (double *) malloc (vertnum*sizeof(double));
	for (i=0; i<vertnum; i++){
	   if (nctype == 0)          /* TWOD_COORDS */
	      if (fscanf(f,"%i%lf%lf", &node, &coord_x, &coord_y) != 3){
		 fprintf(stderr, "\nVrp I/O: error reading NODE_COORD\n\n");
		 exit(1);
	      }
	   if (nctype == 1)          /* THREED_COORDS */
	      if (fscanf(f,"%i%lf%lf%lf", &node, &coord_x, &coord_y,
			 &coord_z) != 4){
		 fprintf(stderr, "\nVrp I/O: error reading NODE_COORD\n\n");
		 exit(1);
	      }
	   dist->coordx[node-1] = coord_x;
	   dist->coordy[node-1] = coord_y;
	   /*since position is an integer and coord is a double, I must
	     round off here if dtype is EXPLICIT*/
	   if (dtype == 0){
	      vrp->posx[node-1] = (int)coord_x;
	      vrp->posy[node-1] = (int)coord_y;
	   }
	   if (nctype == 1) dist->coordz[node-1] = coord_z;
	   if (dist->wtype == _GEO){ /* GEO */
	      /*--- latitude & longitude for node ------------*/
	      deg = (int)(dist->coordx[node-1]);
	      min = dist->coordx[node-1] - deg;
	      dist->coordx[node-1] = MY_PI * (deg + 5.0*min/3.0 ) / 180.0;
	      deg = (int)(dist->coordy[node-1]);
	      min = dist->coordy[node-1] - deg;
	      dist->coordy[node-1] = MY_PI * (deg + 5.0*min/3.0 ) / 180.0;
	   }
	}
	if (fscanf(f,"%i%lf%lf%lf", &node, &coord_x, &coord_y, &coord_z)){
	   fprintf(stderr, "\nVrp I/O: too much data in NODE_COORD\n\n");
	   exit(1);
	}
	break;
      case 11: /* NODE_COORD_TYPE */
	sscanf(line, "%s", tmp);
	for (nctype = 0; nctype < NCTYPE_NUM; nctype++)
	   if (strcmp(nctypes[nctype], tmp) == 0) break;
	if (nctype == NCTYPE_NUM) {
	   fprintf(stderr, "Unknown node_coord_type : %s !!!\n", tmp);
	   exit(1);
	}
	break;
      case 12: /*DEPOT_SECTION*/
	fscanf(f, "%i", &k);
	if (k != 1){
	   fprintf(stderr, "Error in data: depot must be node 1");
	   exit(1);
	}
	vrp->depot = k - 1;
	while (-1 != k) fscanf(f, "%i", &k);
	break;
      case 13: /*CAPACITY_VOL*/
	sscanf(line, "%i", &k);
	capacity_vol = TRUE;
	break;
      case 14: /*DEMAND_SECTION*/
	vrp->demand = (int *) malloc(vertnum*sizeof(int));
	for (i = 0; i < vertnum; i++){
	   if (capacity_vol){
	      if (fscanf(f, "%i%i%i", &k, &l, &m) != 3){
		 fprintf(stderr,"\nVrp I/O: error reading DEMAND_SECTION\n\n");
		 exit(1);
	      }
	   }
	   else if (fscanf(f, "%i%i", &k, &l) != 2){
	      fprintf(stderr, "\nVrp I/O: error reading DEMAND_SECTION\n\n");
	      exit(1);
	   }
	   vrp->demand[k-1] = l;
	   vrp->demand[0] += l;
	}
	if (fscanf(f, "%i%i", &k, &l)){
	   fprintf(stderr, "\nVrp I/O: too much data in DEMAND_SECTION\n\n");
	   exit(1);
	}
	break;
      case 15: /*TIME_WINDOW_SECTION*/  /*These sections are not used*/
	while (fscanf(f, "%d %*d:%*d %*d:%*d", &k));
	break;
      case 16: /*STANDTIME_SECTION*/
	while (fscanf(f, "%d%*d", &k));
	break;
      case 17: /*PICKUP_SECTION*/       
	while (fscanf(f, "%d%*d%*d", &k));
	break;
      case 18: /*  EOF  */
	break;
      case 19: /*  NUMBER_OF_TRUCKS  */
	 if (!sscanf(line, "%i", &k)){
	    fprintf(stderr, "Vrp I/O: error reading NO_OF_TRUCKS\n\n");
	    exit(1);
	 }
	 vrp->numroutes = (int) k;
      default:
	break;
     }
  }
  
  if (f != stdin)
     fclose(f);
  
  /*calculate all the distances explcitly and then use distance type EXPLICIT*/
  
  /*__BEGIN_EXPERIMENTAL_SECTION__*/
  if (vrp->par.bpp_prob){
    dist->cost = (int *) calloc (vrp->edgenum, sizeof(int));
    for (i = 1, k = 0; i < vertnum; i++){
      for (j = 0; j < i; j++){
        dist->cost[k++] = vrp->demand[i]+vrp->demand[j];
      }
    }
    dist->wtype = _EXPLICIT;
  }
  /*___END_EXPERIMENTAL_SECTION___*/
  if (dist->wtype != _EXPLICIT){
    dist->cost = (int *) calloc (vrp->edgenum, sizeof(int));
    for (i = 1, k = 0; i < vertnum; i++){
      for (j = 0; j < i; j++){
         dist->cost[k++] = ICOST(dist, i, j);
      }
    }
    dist->wtype = _EXPLICIT;
  }
  
  if (vrp->par.tsp_prob){
     vrp->capacity = vertnum;
     vrp->numroutes = 1;
     vrp->demand = (int *) malloc (vertnum * ISIZE);
     vrp->demand[0] = vertnum;
     for (i = vertnum - 1; i > 0; i--)
	vrp->demand[i] = 1;
     vrp->cg_par.tsp_prob = TRUE;
     if (!vrp->cg_par.which_tsp_cuts)
	vrp->cg_par.which_tsp_cuts = ALL_TSP_CUTS;
  }
}

/*===========================================================================*/

/*===========================================================================*\
 * This second function reads in the parameters from the parameter file.
\*===========================================================================*/

void vrp_readparams(vrp_problem *vrp, char *filename, int argc, char **argv)
{
   int i, j, k;
   char line[LENGTH], key[50], value[50], c, tmp;
   /*__BEGIN_EXPERIMENTAL_SECTION__*/
   int col_size = 0;
   char v0[10], v1[10];
   /*___END_EXPERIMENTAL_SECTION___*/
   FILE *f = NULL;
   str_int colgen_str[COLGEN_STR_SIZE] = COLGEN_STR_ARRAY;
   
   vrp_params *par = &vrp->par;
#ifdef COMPILE_HEURS
   heur_params *heur_par = &vrp->heur_par;
   lb_params *lb_par = &vrp->lb_par;
#endif
   vrp_lp_params *lp_par = &vrp->lp_par;
   vrp_cg_params *cg_par = &vrp->cg_par;

   if (!strcmp(filename, ""))
      goto EXIT;
   
   if ((f = fopen(filename, "r")) == NULL){
      printf("VRP Readparams: file %s can't be opened\n", filename);
      exit(1); /*error check for existence of parameter file*/
   }

   while(NULL != fgets( line, LENGTH, f)){  /*read in parameter settings*/
      strcpy(key, "");
      sscanf(line, "%s%s", key, value);

      if (strcmp(key, "input_file") == 0){
	 par->infile[MAX_FILE_NAME_LENGTH] = 0;
	 strncpy(par->infile, value, MAX_FILE_NAME_LENGTH);
      }
#ifdef COMPILE_HEURS
      else if (strcmp(key, "rand_seed") == 0){
	 par->rand_seed = (int *) calloc (NUM_RANDS, sizeof(int));
	 if (sscanf(line, "%*s%i%i%i%i%i%i", &par->rand_seed[0],
		    &par->rand_seed[1], &par->rand_seed[2],
		    &par->rand_seed[3], &par->rand_seed[4],
		    &par->rand_seed[5]) != 6)
	    READPAR_ERROR(key);
      }
      else if (strcmp(key, "tours_to_keep") == 0){
	 READ_INT_PAR(par->tours_to_keep);
      }
      else if (strcmp(key, "do_heuristics") == 0){
	 READ_INT_PAR(par->do_heuristics);
      }
      else if (strcmp(key, "ub_time_out") == 0){
	 READ_INT_PAR(par->time_out.ub);
      }
      else if (strcmp(key, "lb_time_out") == 0){
	 READ_INT_PAR(par->time_out.lb);
      }
#endif
      else if (strcmp(key, "k_closest") == 0){
	 READ_INT_PAR(par->k_closest);
      }
      else if (strcmp(key, "k_closest_minimum") == 0){
	 READ_INT_PAR(par->min_closest);
      }
      else if (strcmp(key, "k_closest_maximum") == 0){
	 READ_INT_PAR(par->max_closest);
      }
      else if (strcmp(key, "add_all_edges") == 0){
	 READ_INT_PAR(par->add_all_edges);
      }
      else if (strcmp(key, "base_variable_selection") == 0){
	 READ_INT_PAR(par->base_variable_selection);
      }
      else if (strcmp(key, "use_small_graph") == 0){
	 READ_INT_PAR(par->use_small_graph);
	 if (par->use_small_graph){
	    if (fgets( line, LENGTH, f) == NULL){
	       printf("No small graph file!/n/n");
	       exit(1);
	    }
	    strcpy(key, "");
	    sscanf(line, "%s%s", key, value);
	    if (strcmp(key, "small_graph_file_name") != 0){
	       printf("Need small_graph_file_name next!!!/n/n");
	       exit(1);
	    }
	    strcpy(par->small_graph_file, value);
#ifdef COMPILE_HEURS
	    if (par->use_small_graph == LOAD_SMALL_GRAPH)
	       par->do_heuristics = FALSE;
#endif
	 }
      }
      else if (strcmp(key, "colgen_in_first_phase") == 0 ||
	       strcmp(key, "TM_colgen_in_first_phase") == 0){
	 READ_INT_PAR(par->colgen_strat[0]);
      }
      else if (strcmp(key, "colgen_in_second_phase") == 0 ||
	       strcmp(key, "TM_colgen_in_second_phase") == 0){
	 READ_INT_PAR(par->colgen_strat[1]);
      }
      else if (strcmp(key, "colgen_in_first_phase_str") == 0 ||
	       strcmp(key, "TM_colgen_in_first_phase_str") == 0){
	 READ_STRINT_PAR(par->colgen_strat[0],
			 colgen_str, COLGEN_STR_SIZE, value);
      }
      else if (strcmp(key, "colgen_in_second_phase_str") == 0 ||
	       strcmp(key, "TM_colgen_in_second_phase_str") == 0){
	 READ_STRINT_PAR(par->colgen_strat[1],
			 colgen_str, COLGEN_STR_SIZE, value);
      }
      else if (strcmp(key, "numroutes") == 0){
	 READ_INT_PAR(j);
	 vrp->numroutes = j;
      }

#ifdef COMPILE_HEURS
      /******************** heuristics parameters ****************************/
      
      else if (strcmp(key, "sweep_trials") == 0){
	 READ_INT_PAR(heur_par->sweep_trials);
      }
      else if (strcmp(key, "savings_grid_size") == 0){
	 READ_INT_PAR(heur_par->savings_par.grid_size);
      }
      else if (strcmp(key, "savings_lamda") == 0){
	 READ_FLOAT_PAR(heur_par->savings_par.lamda);
      }
      else if (strcmp(key, "savings_mu") == 0){
	 READ_FLOAT_PAR(heur_par->savings_par.mu);
      }
      else if (strcmp(key, "savings3_grid_size") == 0){
	 READ_INT_PAR(heur_par->savings3_par.grid_size);
      }
      else if (strcmp(key, "savings3_lamda") == 0){
	 READ_FLOAT_PAR(heur_par->savings3_par.lamda);
      }
      else if (strcmp(key, "savings3_mu") == 0){
	 READ_FLOAT_PAR(heur_par->savings3_par.mu);
      }
      else if (strcmp(key, "route_opt1") == 0){
	 READ_INT_PAR(heur_par->route_opt1);
      }
      else if (strcmp(key, "fini_ratio") == 0){
	 READ_FLOAT_PAR(heur_par->fini_ratio);
      }
      else if (strcmp(key, "ni_trials") == 0){
	 READ_INT_PAR(heur_par->ni_trials);
      }
      else if (strcmp(key, "fi_trials") == 0){
	 READ_INT_PAR(heur_par->fi_trials);
      }
      else if (strcmp(key, "fini_trials") == 0){
	 READ_INT_PAR(heur_par->fini_trials);
      }
      else if (strcmp(key, "savings_trials") == 0){
	 READ_INT_PAR(heur_par->savings_par.savings_trials);
      }
      else if (strcmp(key, "savings2_trials") == 0){
	 READ_INT_PAR(heur_par->savings_par.savings2_trials);
      }
      else if (strcmp(key, "savings3_trials") == 0){
	 READ_INT_PAR(heur_par->savings3_par.savings_trials);
      }
      else if (strcmp(key, "near_cluster_trials") == 0){
	 READ_INT_PAR(heur_par->near_cluster_trials);
      }
      else if (strcmp(key, "tsp_fi_trials") == 0){
	 READ_INT_PAR(heur_par->tsp.fi_trials);
      }
      else if (strcmp(key, "tsp_ni_trials") == 0){
	 READ_INT_PAR(heur_par->tsp.ni_trials);
      }
      else if (strcmp(key, "tsp_fini_trials") == 0){
	 READ_INT_PAR(heur_par->tsp.fini_trials);
      }
      else if (strcmp(key, "tsp_num_starts") == 0){
	 READ_INT_PAR(heur_par->tsp.num_starts);
      }
      else if (strcmp(key, "exchange") == 0){
	 READ_INT_PAR(heur_par->exchange);
      }
      else if (strcmp(key, "exchange2") == 0){
	 READ_INT_PAR(heur_par->exchange2);
      }
      else if (strcmp(key, "route_opt2") == 0){
	 READ_INT_PAR(heur_par->route_opt2);
      }
      else if (strcmp(key, "route_opt3") == 0){
	 READ_INT_PAR(heur_par->route_opt3);
      }
      else if (strcmp(key, "lower_bound") == 0){
	 READ_INT_PAR(lb_par->lower_bound);
      }
      else if (strcmp(key, "lb_max_iter") == 0){
	 READ_INT_PAR(lb_par->lb_max_iter);
      }
      else if (strcmp(key, "lb_penalty_mult") == 0){
	 READ_INT_PAR(lb_par->lb_penalty_mult);
      }
#endif
      
      /********************** executable names *******************************/

/*__BEGIN_EXPERIMENTAL_SECTION__*/
      else if (strcmp(key, "winprog_executable_name") == 0){
	 strcpy(par->executables.winprog, value);
      }
/*___END_EXPERIMENTAL_SECTION___*/
#ifdef COMPILE_HEURS
      else if (strcmp(key, "heuristics_executable_name") == 0){
	 strcpy(par->executables.heuristics, value);
      }
#endif
      
      /******************** debugging parameters *****************************/

/*__BEGIN_EXPERIMENTAL_SECTION__*/
      else if (strcmp(key, "winprog_debug") == 0){
	 READ_INT_PAR(par->debug.winprog);
	 CHECK_DEBUG_PAR(par->debug.winprog, key);
      }
/*___END_EXPERIMENTAL_SECTION___*/
#ifdef COMPILE_HEURS
      else if (strcmp(key, "heuristics_debug") == 0){
	 READ_INT_PAR(par->debug.heuristics);
	 CHECK_DEBUG_PAR(par->debug.heuristics, key);
      }
#endif

      /************************ lp parameters *******************************/
      else if (strcmp(key, "branching_rule") == 0){
	 READ_INT_PAR(lp_par->branching_rule);
      }
      else if (strcmp(key, "branch_on_cuts") == 0){
	 READ_INT_PAR(lp_par->branch_on_cuts);
      }
      else if (strcmp(key, "strong_branching_cand_num") == 0){
	 READ_INT_PAR(lp_par->strong_branching_cand_num_max);
	 lp_par->strong_branching_cand_num_min =
	    lp_par->strong_branching_cand_num_max;
	 lp_par->strong_branching_red_ratio = 0;
      }
      else if (strcmp(key, "strong_branching_cand_num_min") == 0){
	 READ_INT_PAR(lp_par->strong_branching_cand_num_min);
      }
      else if (strcmp(key, "strong_branching_cand_num_max") == 0){
	 READ_INT_PAR(lp_par->strong_branching_cand_num_max);
      }
      else if (strcmp(key, "strong_branching_red_ratio") == 0){
	 READ_INT_PAR(lp_par->strong_branching_red_ratio);
      }
      else if (strcmp(key, "child_compar_obj_tol") == 0){
	 READ_FLOAT_PAR(lp_par->child_compar_obj_tol);
      }
      else if (strcmp(key, "detect_tailoff") == 0){
	 READ_INT_PAR(lp_par->detect_tailoff);
      }

      /************************* cutgen parameters ***************************/

      else if (strcmp(key, "verbosity") == 0){
	 READ_INT_PAR(par->verbosity);
	 lp_par->verbosity = cg_par->verbosity = par->verbosity;
      }
      else if (strcmp(key, "do_greedy") == 0){
	 READ_INT_PAR(cg_par->do_greedy);
      }
      else if (strcmp(key, "greedy_num_trials") == 0){
	 READ_INT_PAR(cg_par->greedy_num_trials);
      }
      else if (strcmp(key, "do_extra_in_root") == 0){
	 READ_INT_PAR(cg_par->do_extra_in_root);
      }
      else if (strcmp(key, "which_tsp_cuts") == 0){
	 READ_INT_PAR(cg_par->which_tsp_cuts);
      }
      /*__BEGIN_EXPERIMENTAL_SECTION__*/
      else if (strcmp(key, "do_mincut") == 0){
	 READ_INT_PAR(cg_par->do_mincut);
      }
      else if (strcmp(key, "always_do_mincut") == 0){
	 READ_INT_PAR(cg_par->always_do_mincut);
      }
      else if (strcmp(key, "update_contr_above") == 0){
	 READ_INT_PAR(cg_par->update_contr_above);
      }
      else if (strcmp(key, "shrink_one_edges") == 0){
	 READ_INT_PAR(cg_par->shrink_one_edges);
      }
      else if (strcmp(key, "do_extra_checking") == 0){
	 READ_INT_PAR(cg_par->do_extra_checking);
      }
      /*___END_EXPERIMENTAL_SECTION___*/
#if defined(CHECK_CUT_VALIDITY) || defined(TRACE_PATH)
      else if (strcmp(key, "feasible_solution_edges") == 0){
	 READ_INT_PAR(vrp->feas_sol_size);
	 if (vrp->feas_sol_size){
	    vrp->feas_sol = (int *)calloc(vrp->feas_sol_size, sizeof(int));
	    for (i=0; i<vrp->feas_sol_size; i++){
	       if (!fgets( line, LENGTH, f)){
		  fprintf(stderr,
			  "\nVrp I/O: error reading in feasible solution\n\n");
		  exit(1);
	       }
	       strcpy(key, "");
	       sscanf(line, "%s%s", key, value);
	       if (strcmp(key, "edge")){
		  fprintf(stderr,
			  "\nVrp I/O: error reading in feasible solution\n\n");
		  exit(1);
	       }
	       if (sscanf(value, "%i", vrp->feas_sol+i) != 1){
		  fprintf(stderr,
		  "\nVrp I/O: error reading in feasible solution %s\n\n",
			  key);
		  exit(1);
	       }
	    }
	 }
      }
      else if (strcmp(key, "feasible_solution_nodes") == 0){
	 READ_INT_PAR(vrp->feas_sol_size);
	 if (vrp->feas_sol_size){
	    int cur_node, prev_node = 0;
	    
	    vrp->feas_sol = (int *)calloc(vrp->feas_sol_size, sizeof(int));
	    for (i=0; i<vrp->feas_sol_size; i++){
	       if (!fgets( line, LENGTH, f)){
		  fprintf(stderr,
			  "\nVrp I/O: error reading in feasible solution\n\n");
		  exit(1);
	       }
	       sscanf(line, "%s", value);
	       if (sscanf(value, "%i", &cur_node) != 1){
		  fprintf(stderr,
			"\nVrp I/O: error reading in feasible solution %s\n\n",
			  key);
		  exit(1);
	       }else{
		  vrp->feas_sol[i] = INDEX(prev_node, cur_node);
		  prev_node = cur_node;
	       }
	    }
	 }
      }
#endif
      else if (strcmp(key, "which_connected_routine") == 0){
	 READ_INT_PAR(cg_par->which_connected_routine);
      }
      else if (strcmp(key, "max_num_cuts_in_shrink") == 0){
	 READ_INT_PAR(cg_par->max_num_cuts_in_shrink);
      }
/*__BEGIN_EXPERIMENTAL_SECTION__*/
#ifdef COMPILE_DECOMP
      else if (strcmp(key, "allow_one_routes_in_bfm") == 0){
	 READ_INT_PAR(cg_par->allow_one_routes_in_bfm);
      }
      else if (strcmp(key, "follow_one_edges") == 0){
	 READ_INT_PAR(cg_par->follow_one_edges);
      }
      else if (strcmp(key, "col_gen_grid_size") == 0){
	 READ_INT_PAR(cg_par->col_gen_par.grid_size);
      }
      else if (strcmp(key, "col_gen_lamda") == 0){
	 READ_FLOAT_PAR(cg_par->col_gen_par.lambda);
      }
      else if (strcmp(key, "col_gen_mu") == 0){
	 READ_FLOAT_PAR(cg_par->col_gen_par.mu);
      }
      else if (strcmp(key, "max_num_columns") == 0){
	 READ_INT_PAR(cg_par->max_num_columns);
      }
#endif
#ifdef COMPILE_OUR_DECOMP
      else if (strcmp(key, "generate_farkas_cuts") == 0){
	 READ_INT_PAR(cg_par->generate_farkas_cuts);
      }
      else if (strcmp(key, "generate_capacity_cuts") == 0){
	 READ_INT_PAR(cg_par->generate_capacity_cuts);
      }
      else if (strcmp(key, "generate_no_cols_cuts") == 0){
	 READ_INT_PAR(cg_par->generate_no_cols_cuts);
      }
      else if (strcmp(key, "decomp_decompose") == 0){
	 READ_INT_PAR(cg_par->decomp_decompose);
      }
      else if (strcmp(key, "feasible_tours_only") == 0){
	 READ_INT_PAR(cg_par->feasible_tours_only);
      }
      else if (strcmp(key, "graph_density_threshold") == 0){
	 READ_FLOAT_PAR(cg_par->graph_density_threshold);
      }
      else if (strcmp(key, "gap_threshold") == 0){
	 READ_FLOAT_PAR(cg_par->gap_threshold);
      }
      else if (strcmp(key, "do_our_decomp") == 0){
	 READ_INT_PAR(cg_par->do_our_decomp);
      }
      else if (strcmp(key, "do_decomp_once") == 0){
	 READ_INT_PAR(cg_par->do_decomp_once);
      }
#endif
      /******************** sol pool **************************/
      else if (strcmp(key, "sol_pool_col_size") == 0){
	 READ_INT_PAR(col_size);
      }
      else if (strcmp(key, "sol_pool_col_num") == 0){
	 if (col_size == 0){
	    fprintf(stderr, "Column size is 0 -- exiting\n\n");
	    exit(1);
	 }
	 READ_INT_PAR(vrp->sol_pool_col_num);
	 vrp->sol_pool_cols = (int *) calloc (2*vrp->sol_pool_col_num*col_size,
					      sizeof(int));
	 vrp->sol_pool_col_num = 0;
      }
      else if (strcmp(key, "sol_pool_col") == 0){
	 if (col_size == 0){
	    fprintf(stderr, "Column size is 0 -- exiting\n\n");
	    exit(1);
	 }
	 for(i = vrp->sol_pool_col_num*2*col_size;
	     i < (vrp->sol_pool_col_num+1)*2*col_size;
	     i+=2){
	    if (!fgets( line, LENGTH, f)){
	       fprintf(stderr,
		       "\nVrp I/O: error reading in feasible solution\n\n");
	       exit(1);
	    }
	    strcpy(key,"");
	    sscanf(line,"%s%s%s", key, v0, v1);
	    if (strcmp(key,"edge")){
	       fprintf(stderr,
		       "\nVrp I/O: error reading in feasible solution\n\n");
	       exit(1);
	    }
	    if (sscanf(v0, "%i", vrp->sol_pool_cols+i) != 1){
	       fprintf(stderr, "\nVrp I/O: error reading in solution %s\n\n",
		      key);
	       exit(1);
	    }
	    if (sscanf(v1, "%i", vrp->sol_pool_cols+i+1) != 1){
	       fprintf(stderr, "\nVrp I/O: error reading in solution %s\n\n",
		      key);
	       exit(1);
	    }
	 }
	 vrp->sol_pool_col_num++;
      }
/*___END_EXPERIMENTAL_SECTION___*/
   }

EXIT:
   
   for (i = 1; i < argc; i++){
      sscanf(argv[i], "%c %c", &tmp, &c);
      if (tmp != '-')
	 continue;
      switch (c) {
       case 'H':
	 user_usage();
	 exit(0);
       case 'E':
	 par->add_all_edges = FALSE;
	 break;
       case 'S':
	 strncpy(par->small_graph_file, argv[++i], MAX_FILE_NAME_LENGTH);
	 par->use_small_graph = LOAD_SMALL_GRAPH;
	 break;
       case 'F':
	 strncpy(par->infile, argv[++i], MAX_FILE_NAME_LENGTH);
	 break;
       case 'B':
	 sscanf(argv[++i], "%i", &lp_par->branching_rule);
	 break;
       case 'A':
	 sscanf(argv[++i], "%i", &par->base_variable_selection);
	 break;
       case 'V':
	 sscanf(argv[++i], "%i", &par->verbosity);
	 break;
       case 'K':
	 sscanf(argv[++i], "%i", &par->k_closest);
	 break;
       case 'N':
	 sscanf(argv[++i], "%i", &vrp->numroutes);
	 break;
       case 'R':
	 par->tsp_prob = TRUE;
	 break;
       case 'C':
	 sscanf(argv[++i], "%i", &vrp->capacity);
	 break;
       case 'T':
	 par->test = TRUE;
	 if(i+1 < argc){
	   sscanf(argv[i+1], "%c", &tmp);
	   if(tmp != '-'){
	     strncpy(par->test_dir, argv[++i],MAX_FILE_NAME_LENGTH);
	   }
	 }
	 break;
      };
   }

   if (f)
      fclose(f);
   
#ifdef COMPILE_HEURS
   if (!par->rand_seed){
      par->rand_seed = (int *) calloc (NUM_RANDS, sizeof(int));
      for (k = 0; k<NUM_RANDS; k++)
	 par->rand_seed[k] = k+12;
   }
   
   if (heur_par->route_opt1 < 0)
      heur_par->route_opt1 = par->tours_to_keep;
   if (heur_par->route_opt2 < 0)
      heur_par->route_opt2 = par->tours_to_keep;
   if (heur_par->route_opt3 < 0)
      heur_par->route_opt3 = par->tours_to_keep;
   if (heur_par->exchange < 0)
      heur_par->exchange = par->tours_to_keep;
   if (heur_par->exchange2 < 0)
      heur_par->exchange2 = par->tours_to_keep;
#endif
}

/*===========================================================================*/

void vrp_set_defaults(vrp_problem *vrp)
{
   vrp_params *par = &vrp->par;
#ifdef COMPILE_HEURS
   heur_params *heur_par = &vrp->heur_par;
   lb_params *lb_par = &vrp->lb_par;
#endif
   vrp_lp_params *lp_par = &vrp->lp_par;
   vrp_cg_params *cg_par = &vrp->cg_par;

   /*vrp->numroutes = 0;*/
#if defined(CHECK_CUT_VALIDITY) || defined(TRACE_PATH)
   vrp->feas_sol_size = 0;
   vrp->feas_sol = NULL;
#endif
   par->tsp_prob = FALSE;
#ifdef COMPILE_HEURS
   par->rand_seed = NULL;
   par->tours_to_keep = 15;
   par->do_heuristics = FALSE;
#endif
   par->k_closest = -1;
   par->min_closest = 4;
   par->max_closest = 10;
   par->add_all_edges = TRUE;
   par->base_variable_selection = SOME_ARE_BASE;
   par->use_small_graph = FALSE;
   par->colgen_strat[0] = 0;
   par->colgen_strat[1] = 0;
   par->verbosity = 9;
   /*__BEGIN_EXPERIMENTAL_SECTION__*/
   par->debug.winprog = 0;
   /*___END_EXPERIMENTAL_SECTION___*/
#ifdef COMPILE_HEURS
   par->debug.heuristics = 0;
   par->time_out.ub = 60;
   par->time_out.lb = 60;
   heur_par->no_of_machines = 3;
   heur_par->sweep_trials = 1000;        /*default parameter settings*/
   heur_par->savings_par.savings_trials = 0;
   heur_par->savings_par.savings2_trials = 1;
   heur_par->savings_par.grid_size = 1;
   heur_par->savings_par.mu = 1;
   heur_par->savings_par.lamda = 2;
   heur_par->savings3_par.savings_trials = 1;
   heur_par->savings3_par.grid_size = 1;
   heur_par->savings3_par.mu = 1;
   heur_par->savings3_par.lamda = 2;
   heur_par->route_opt1 = -1;
   heur_par->route_opt2 = -1;
   heur_par->route_opt3 = -1;
   heur_par->fini_ratio = 0;
   heur_par->ni_trials = 1;
   heur_par->fi_trials = 1;
   heur_par->fini_trials = 1;
   heur_par->near_cluster_trials = 1;
   heur_par->tsp.fi_trials = 3;
   heur_par->tsp.ni_trials = 3;
   heur_par->tsp.fini_trials = 3;
   heur_par->tsp.num_starts = 1000;
   heur_par->exchange = -1;
   heur_par->exchange2 = -1;
   lb_par->lower_bound = 0;
   lb_par->lb_max_iter = 200;
   lb_par->lb_penalty_mult = 100;
   vrp->lb = (low_bd *) calloc (1, sizeof(low_bd));
   strcpy(par->executables.heuristics, "vrp_heuristics");
#endif
   
   lp_par->verbosity = 0;
   lp_par->branching_rule = 2;
   lp_par->branch_on_cuts = FALSE;
   lp_par->strong_branching_cand_num_max = 7;
   lp_par->strong_branching_cand_num_min = 7;
   lp_par->strong_branching_red_ratio = 0;
   lp_par->detect_tailoff  = 0;
   lp_par->child_compar_obj_tol = .01;

   cg_par->verbosity = 0;
   cg_par->do_greedy = 1;
   cg_par->greedy_num_trials = 5;
   cg_par->do_extra_in_root = FALSE;
   cg_par->which_tsp_cuts = NO_TSP_CUTS;
   cg_par->which_connected_routine = BOTH;
   cg_par->max_num_cuts_in_shrink = 200;
   /*__BEGIN_EXPERIMENTAL_SECTION__*/
   cg_par->do_mincut = 0;
   cg_par->always_do_mincut = 0;
   cg_par->update_contr_above = 0;
   cg_par->shrink_one_edges = 1;
   cg_par->do_extra_checking = 0;
#ifdef COMPILE_DECOMP
   cg_par->generate_farkas_cuts = TRUE;
   cg_par->generate_no_cols_cuts = TRUE;
   cg_par->generate_capacity_cuts = TRUE;
   cg_par->decomp_decompose = FALSE;
   cg_par->allow_one_routes_in_bfm = TRUE;
   cg_par->follow_one_edges = TRUE;
   cg_par->max_num_columns = 1000; 
   cg_par->col_gen_par.grid_size = 1;
   cg_par->col_gen_par.lambda = 2;
   cg_par->col_gen_par.mu = 1;
#endif
#ifdef COMPILE_OUR_DECOMP
   cg_par->feasible_tours_only = FALSE;
   cg_par->graph_density_threshold = 10;
   cg_par->gap_threshold = -1;
   cg_par->do_our_decomp = FALSE;
   cg_par->do_decomp_once = TRUE;
#endif
   /*___END_EXPERIMENTAL_SECTION___*/
      
   return;
}

/*===========================================================================*/
/*===========================================================================*/

void vrp_create_instance(void *user, int vertnum, int numroutes, int capacity,
			 int *demand, int *cost, small_graph *g)
{
   vrp_problem *vrp = (vrp_problem *)user;
   int edgenum = vertnum*(vertnum-1)/2;

   vrp->vertnum = vertnum;
   vrp->numroutes = numroutes;
   vrp->capacity = capacity;
   vrp->demand = (int *) malloc(vertnum*ISIZE);
   memcpy(vrp->demand, demand, vertnum*ISIZE);
   vrp->dist.cost = (int *) malloc(edgenum*ISIZE);
   memcpy(vrp->dist.cost, cost, edgenum*ISIZE);
   vrp->dist.wtype = _EXPLICIT;
   if (g){
      vrp->g = (small_graph *) malloc(sizeof(small_graph));
      memcpy(vrp->g, g, sizeof(small_graph));
      vrp->g->edges = (edge_data *) malloc (vrp->g->edgenum*sizeof(edge_data));
      memcpy(vrp->g->edges, g->edges, vrp->g->edgenum*sizeof(edge_data));
   }
   
   strcpy(vrp->par.infile, "");
   
   return;
}
