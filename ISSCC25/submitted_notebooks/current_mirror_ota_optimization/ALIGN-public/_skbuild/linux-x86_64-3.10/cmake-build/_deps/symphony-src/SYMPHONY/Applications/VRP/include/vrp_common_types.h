/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* the Vehicle Routing Problem and the Traveling Salesman Problem.           */
/*                                                                           */
/* (c) Copyright 2000-2013 Ted Ralphs. All Rights Reserved.                  */
/*                                                                           */
/* This application was developed by Ted Ralphs (ted@lehigh.edu)             */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

#ifndef _VRP_COMMON_TYPES_H
#define _VRP_COMMON_TYPES_H

/*---------------------------------------------------------------------*\
| This _node data structure holds information about a customer node in  |
| a tour. The next field contains the index of the node that is next    |
| on the current route or if the current node is the last on eon its    |
| route, it contains the index of the first node on the next route.     |
| The route number field contains the number of the route that the      |
| node is on. This information is maintained to make reconstruction of  |
| the route and calculation of the route cost possible                  |
\*---------------------------------------------------------------------*/

typedef struct _NODE{
   int next;
   int route;
}_node;

/*--------------------------------------------------------------------*\
| This data structure contains information about a tour's route        |
| structure. Specifically, first and last are the first and last nodes |
| on a particular route, numcust is the number of customers on the     |
| route and cost is the cost of that route. The routes are always      |
| numbered starting at 1 for convenience in certain calculations so    |
| route_info[0] always contains 0 in all fields.                       |
\*--------------------------------------------------------------------*/

typedef struct ROUTE_DATA{
   int first;
   int last;
   int numcust;
   int weight;
   int cost;
}route_data;

/*--------------------------------------------------------------------*\
| The best_tours data structure is for storing tours for later use. The|
| cost field contains the total cost of the tour. The numroutes field  |
| contains the number of trucks used in the tour and the tour field is |
| a pointer to an array which specifies the order of each of the       |
| routes as explained above. The field route_info contains             |
| information about the tour's routes as explained above               |
\*--------------------------------------------------------------------*/
typedef struct BEST_TOURS{
   int algorithm;
   double solve_time;
   int cost;
   int numroutes;
   route_data *route_info;
   _node *tour;
}best_tours;

/*--------------------------------------------------------------------*\
| Stores the method by which distances should be calculated            |
\*--------------------------------------------------------------------*/

typedef struct DISTANCES{
   int         wtype;
   int        *cost;
   double     *coordx;
   double     *coordy;
   double     *coordz;
}distances;

/*--------------------------------------------------------------------*\
| This structure contains information about a particular edge          |
\*--------------------------------------------------------------------*/

typedef struct EDGE_DATA{
  int v0;      
  int v1;
  int cost;
}edge_data;

typedef struct DBL_EDGE_DATA{
  int v0;      
  int v1;
  double cost;
}dbl_edge_data;

#endif
