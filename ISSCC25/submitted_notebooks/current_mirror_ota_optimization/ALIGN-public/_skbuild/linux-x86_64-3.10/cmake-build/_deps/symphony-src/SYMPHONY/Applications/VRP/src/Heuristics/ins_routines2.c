/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* the Vehicle Routing Problem and the Traveling Salesman Problem.           */
/*                                                                           */
/* This application was developed by Ted Ralphs (ted@lehigh.edu)             */
/* This file was modified by Ali Pilatin January, 2005 (alp8@lehigh.edu)     */
/*                                                                           */
/* (c) Copyright 2000-2005 Ted Ralphs. All Rights Reserved.                  */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

#include <math.h>

#include "sym_constants.h"
#include "ins_routines2.h"
#include "sweep.h"
#include "qsort.h"
#include "sym_messages.h"
#include "vrp_const.h"
#include "sym_proccomm.h"
#include "compute_cost.h"
#include "heur_routines.h"
#include <string.h>
#include <stdio.h>
/*------------------------------------------------------------------------*\
| These routines are associated with the near_cluster algorithm. They are  |
| very similar to those used for the nearest insert heuristic for the TSP  |
\*------------------------------------------------------------------------*/

void nearest_ins2(heur_prob *p, _node *tour, route_data *route_info, 
		 int from_size, int to_size, neighbor *nbtree, 
		 int *intour, int *last, int *zero_cost)
{
	int nearnode, size, host;
	int *demand = p->demand;
	int capacity = p->capacity;
	
	for (size = from_size; size < to_size;){

	  /* Get the node nearest to a particular route and its host */

	  nearnode = closest2(nbtree, intour, last, &host);

	  /*--------------------------------------------------------------*\
	  | Check the feasibility of inserting this node on its host route |
          | If it is feasible, insert it. If not, get a new host for that  |
          | node and add it back into the binary tree                      |
          \*--------------------------------------------------------------*/

	  if (route_info[tour[host].route].weight + demand[nearnode]
	      <= capacity){
	    intour[nearnode] = IN_TOUR;
	    tour[nearnode].route = tour[host].route;
	    route_info[tour[nearnode].route].cost += insert_into_tour2
	      (p, tour, nearnode, route_info);
	    ni_insert_edges2(p, nearnode, nbtree, intour, last, tour, route_info);
	    size++;
	  }
	  else{
	    intour[nearnode] = NOT_NEIGHBOR;
	    new_host2(p, nearnode, nbtree, intour, last, tour, route_info, zero_cost);
	  }
	}
	return;
}

/*===========================================================================*/

int closest2(neighbor *nbtree, int *intour, int *last, int *host)
{
  int closest_node;
  int pos, ch;
  int cost;
  neighbor temp;

  /*-----------------------------------------------------------------------*\
  | This routine deletes the item from the top of the binary tree where the |
  | distances are stored and adjusts the tree accordingly                   |
  \*-----------------------------------------------------------------------*/
    
  closest_node = nbtree[1].nbor;  
  *host = nbtree[1].host;
  (void) memcpy ((char *)&temp, (char *)(nbtree+*last), sizeof(neighbor));
  cost = nbtree[*last].cost;
  --*last;
  pos = 1;
  while ((ch=2*pos) < *last){
    if (nbtree[ch].cost > nbtree[ch+1].cost)
      ch++;
    if (cost <= nbtree[ch].cost)
      break;
    intour[nbtree[ch].nbor] = pos;
    (void) memcpy ((char *)(nbtree+pos), 
		   (char *)(nbtree+ch), sizeof(neighbor));
    pos = ch;
  }
  if (ch == *last){
    if (cost > nbtree[ch].cost){
      intour[nbtree[ch].nbor] = pos;
      (void) memcpy ((char *)(nbtree+pos), 
		     (char *)(nbtree+ch), sizeof(neighbor));
      pos=ch;
    }
  }
  intour[temp.nbor] = pos;
  (void) memcpy ((char *)(nbtree+pos), (char *)&temp, sizeof(neighbor));
  return(closest_node);
}

/*===========================================================================*/

void ni_insert_edges2(heur_prob *p, int new_node, neighbor *nbtree, int *intour, 
		     int *last, _node *tour, route_data *route_info)

     /*-----------------------------------------------------------------------*\
     |  Scan through the edges incident to 'new_node' - the new node in the set.    |
     |  If the other end 'i' is in the set, do nothing.                        |
     |  If the other end is not in nbtree then insert it.                      |
     |  Otherwise update its distance if necessary:                            |
     |     If the previous closest point of the set to 'i' is closer then      |
     |     'new_node' then we don't have to do anything, otherwise update.          |
     |     (update: the min element is on the top of the tree                  |
     |              Therefore the insertion and the update parts can be done   |
     |              with the same code, not like in fi_insert_edges.)          |
     \*-----------------------------------------------------------------------*/

{
  int cost, prevcost;
  int pos, ch;
  int i;
  int vertnum = p->vertnum;
  int *demand = p->demand;
  int capacity = p->capacity;
  
  for (i=1; i<vertnum; i++){
    if ((intour[i] != IN_TOUR) && 
	(demand[i]+route_info[tour[new_node].route].weight<=capacity)){
      cost = ICOST(&p->dist, i, new_node);
      if (intour[i] == NOT_NEIGHBOR){
	pos = ++(*last);
	prevcost = cost+1;
      }else{
	prevcost = nbtree[pos = intour[i]].cost;
      }
      if (prevcost > cost){
	while ((ch=pos/2) != 0){
	  if (nbtree[ch].cost <= cost)
	    break;
	  intour[nbtree[ch].nbor] = pos;
	  (void) memcpy ((char *)(nbtree+pos), 
			 (char *)(nbtree+ch), sizeof(neighbor));
	  pos = ch;
	}
	nbtree[pos].nbor = i;
	nbtree[pos].host = new_node;
	nbtree[pos].cost = cost;
	intour[i] = pos;
      }
    }
  }
}
	
/*===========================================================================*/

int insert_into_tour2(heur_prob *p, _node *tour, int new_node, 
		     route_data *route_info)
{
  int change, minchange;
  int iminchange = 0;
  int v0=0, v1;
  int cur_route;

  cur_route = tour[new_node].route;
  v1 = route_info[cur_route].first;

  /*-------------------------------------------------------------------------*\
  | Here we search for the cheapest place to insert the new customer on the   |
  | tour and insert it in that position. Then tour and route_info data        |
  | structures must be updated accordingly                                    |
  \*-------------------------------------------------------------------------*/
	
  minchange = ICOST(&p->dist, v0, new_node) + ICOST(&p->dist, new_node, v1) - ICOST(&p->dist, v0, v1);
  do{
    v0 = v1;
    v1 = tour[v0].next;
    change = ICOST(&p->dist, v0,new_node) + ICOST(&p->dist, new_node,v1) - ICOST(&p->dist, v0,v1);
    if (change < minchange){
      minchange = change;
      iminchange = v0;
    }
  }while (v1); /* check to see if we've reached the end of the route yet */
  if (iminchange){
    v1 = tour[v0 = iminchange].next;
    tour[new_node].next = v1;
    tour[v0].next = new_node;
  }
  else{
    v1 = route_info[cur_route].first;
    tour[new_node].next = v1;
    route_info[cur_route].first = new_node;
  }
  route_info[cur_route].weight += p->demand[new_node];
  route_info[cur_route].numcust++;
  if (v1 == 0){
    route_info[cur_route].last = new_node;
  }
  return(minchange);
}

/*===========================================================================*/

void new_host2(heur_prob *p, int node, neighbor *nbtree, int *intour, 
	      int *last, _node *tour, route_data *route_info, int *zero_cost)
{
  int cost = 0, prevcost;
  int pos, ch;
  int i;
  int cur_route, r_bufid, parent, info;
  int numroutes = p->cur_tour->numroutes;
  int vertnum = p->vertnum;
  int *demand = p->demand;
  int capacity = p->capacity;

  /*-------------------------------------------------------------------------*\
  | As mentioned earlier, it may be the case that a customer cannot be        |
  | inserted on its host route because of capacity restrictions. In this case |
  | we must look for a new host. In the case that a new host cannot be found  |
  | (i.e. the customer cannot be inserted on any route), the algorithm fails  |
  | and sends the current partial solution back with a cost of zero which     |
  | indicates that an error was encountered. The following loop searches all  |
  | all customers in the current solution and takes as host the closest       |
  | customer to whose route the customer in question can be feasibly added    |
  \*-------------------------------------------------------------------------*/ 
  
  for (i = 1; i<vertnum; i++){
    if ((intour[i] == IN_TOUR) &&
	(route_info[tour[i].route].weight + demand[node] <= capacity)){
      cost = ICOST(&p->dist, node, i);
      if (intour[node] == NOT_NEIGHBOR){
	pos = ++(*last);
	prevcost = cost+1;
      }else{
	prevcost = nbtree[pos = intour[node]].cost;
      }
      if (prevcost > cost){
	while ((ch=pos/2) != 0){
	  if (nbtree[ch].cost <= cost)
	    break;
	  intour[nbtree[ch].nbor] = pos;
	  (void) memcpy ((char *)(nbtree+pos), 
			 (char *)(nbtree+ch), sizeof(neighbor));
	  pos = ch;
	}
	nbtree[pos].nbor = node;
	nbtree[pos].host = i;
	nbtree[pos].cost = cost;
	intour[node] = pos;
      }
    }
  }
  if (!intour[node]){ /* if there is no feasible insertion point, then abort */
    printf(
       "\n\nError: customer cannot be inserted on any route .... aborting!\n");
    tour[0].next = route_info[1].first;

    /*-----------------------------------------------------------------------*\
    | This loop points the last node of each route to the first node of the   |
    | next route. At the end of this procedure, the last node of each route is|
    | pointing at the depot, which is not what we want.                       |
    \*-----------------------------------------------------------------------*/
    for (cur_route = 1; cur_route< numroutes; cur_route++)
      tour[route_info[cur_route].last].next = route_info[cur_route+1].first;
    cost = 0;
    *zero_cost = 1;
    
    parent = pvm_parent();
    
    /*-----------------------------------------------------------------------*/
    /* Transmit the partial tour back to the parent with cost zero (error)   */
    /*-----------------------------------------------------------------------*/
    
    send_tour(tour, cost, numroutes, NEAR_CLUSTER, (double) 0, parent, 
	      vertnum, 1, route_info);
	
    if ( nbtree ) free ((char *) nbtree);
    if ( intour ) free ((char *) intour);

    free_heur_prob(p);
	
  }
  return;
}

/*===========================================================================*/

void seeds2(heur_prob *p, int *numroutes, int *intour, neighbor *nbtree)
{
  sweep_data *data;
  float depotx, depoty;
  float tempx, tempy;
  int i, cur_route = 0, cur_node;
  int weight = 0;
  int last;
  int vertnum = p->vertnum, farnode;
  int *demand = p->demand;
  int capacity = p->capacity;
  _node *tour = p->cur_tour->tour;
  route_data *route_info = NULL;

  /*-------------------------------------------------------------------*\
  | The algorithm for calculating seed customers first clusters the     |
  | customers as in the sweep heuristic and then takes the customer in  |
  | each cluster that is farthest from the depot as the seed for a route|
  \*-------------------------------------------------------------------*/

  if (!*numroutes){
    data = (sweep_data *)calloc(vertnum-1, sizeof(sweep_data));
    depotx = p->dist.coordx[0];
    depoty = p->dist.coordy[0];
    
    /*calculate angles for sorting*/
    
    for (i=0; i<vertnum-1; i++){
      tempx = p->dist.coordx[i+1] - depotx;
      tempy = p->dist.coordy[i+1] - depoty;
      data[i].angle = (float) atan2(tempy, tempx);
      if (data[i].angle < 0) data[i].angle += 2*M_PI;
      data[i].cust=i+1;
    }
    
    quicksort(data, vertnum-1);
    
    for (i=0; i<vertnum-1; i++){
      if ((weight + demand[data[i].cust] <= capacity) && (cur_route))
	weight +=  demand[data[i].cust];
      else{
	cur_route++;
	weight = demand[data[i].cust];
      }
    }
    *numroutes = cur_route;
    free((char *) data);
  }

  route_info = p->cur_tour->route_info
             = (route_data *) calloc ((*numroutes)+1, sizeof(route_data));

  last = 0;
  intour[0] = IN_TOUR;
  fi_insert_edges2(p, 0, nbtree, intour, &last);
  farnode = farthest2(nbtree, intour, &last);
  intour[farnode] = IN_TOUR;
  fi_insert_edges2 (p, farnode, nbtree, intour, &last);
  tour[farnode].next = 0;
  tour[0].next = farnode;
  farthest_ins_from_to2(p, tour, 2, *numroutes+1, nbtree, intour, &last);

  for (cur_route = 1, cur_node = tour[0].next;
       cur_route <= *numroutes; cur_route++, cur_node = tour[cur_node].next){
    route_info[cur_route].first = route_info[cur_route].last
                                = cur_node;
    route_info[cur_route].weight = p->demand[cur_node];
    route_info[cur_route].numcust++;
    tour[cur_node].route = cur_route;
    route_info[cur_route].cost = 2*ICOST(&p->dist, 0, cur_node);
  }
}
  
/*===========================================================================*/

void farthest_ins_from_to2(heur_prob *p, _node *tour, int from_size, 
			 int to_size, neighbor *nbtree, 
			 int *intour, int *last)
{
  int farnode, size;
  int minchange, change;
  int i;
  int v0, v1, iminchange = 0;
  
  for (size = from_size; size < to_size; size++){
    farnode = farthest2(nbtree, intour, last);
    intour[farnode] = IN_TOUR;
    for (i=0, minchange = MAXINT, v1=0; i<size; i++){
      v0 = v1;
      v1 = tour[v0].next;
      change = (ICOST(&p->dist, v0, farnode) + ICOST(&p->dist, farnode,v1))
	 - ICOST(&p->dist, v0,v1);
      if (change < minchange){
	minchange = change;
	iminchange = v0;
      }
    }
    v1 = tour[v0 = iminchange].next;
    tour[farnode].next = v1;
    tour[v0].next = farnode;
    fi_insert_edges2(p, farnode, nbtree, intour, last);
  }
}

/*===========================================================================*/

int farthest2(neighbor *nbtree, int *intour, int *last)
{
  int farthest_node;
  int pos, ch;
  int cost;
  neighbor temp;

  /*-----------------------------------------------------------------------*\
  | This routine deletes the item from the top of the binary tree where the |
  | distances are stored and adjusts the tree accordingly                   |
  \*-----------------------------------------------------------------------*/
  
  farthest_node = nbtree[1].nbor;
  (void) memcpy ((char *)&temp, (char *)(nbtree+*last), sizeof(neighbor));
  cost = nbtree[*last].cost;
  --*last;
  pos = 1;
  while ((ch=2*pos) < *last){
    if (nbtree[ch].cost < nbtree[ch+1].cost)
      ch++;
    if (cost >= nbtree[ch].cost)
      break;
    intour[nbtree[ch].nbor] = pos;
    (void) memcpy ((char *)(nbtree+pos), 
		   (char *)(nbtree+ch), sizeof(neighbor));
    pos = ch;
  }
  if (ch == *last){    if (cost < nbtree[ch].cost){
      intour[nbtree[ch].nbor] = pos;
      (void) memcpy ((char *)(nbtree+pos), 
		     (char *)(nbtree+ch), sizeof(neighbor));
      pos=ch;
    }
  }
  intour[temp.nbor] = pos;
  (void) memcpy ((char *)(nbtree+pos), (char *)&temp, sizeof(neighbor));
  return(farthest_node);
}

/*===========================================================================*/

void fi_insert_edges2(heur_prob *p, int new_node, neighbor *nbtree, int *intour,
		     int *last)
     /*-----------------------------------------------------------------------*\
     |  Scan through the edges incident to 'new_node' - the new node in the set.    |
     |  If the other end 'i' is in the set, do nothing.                        |
     |  If the other end is not in nbtree then insert it.                      |
     |  Otherwise update its distance if necessary:                            |
     |     If the previous closest point of the set to 'i' is closer then      |
     |     'new_node' then we don't have to do anything, otherwise update.          |
     |     (update: the max element is on the top of the tree)                 |
     \*-----------------------------------------------------------------------*/
{
  int cost;
  int pos, ch;
  int i;
  int vertnum = p->vertnum;
  
  for (i=0; i<vertnum; i++){
    if ( intour[i] != IN_TOUR){
      cost = ICOST(&p->dist, i, new_node);
      if (intour[i] == NOT_NEIGHBOR){ /* new neighbor, must insert it */
	pos = ++(*last);
	while ((ch=pos/2) != 0){
	  if (nbtree[ch].cost >= cost)
	    break;
	  intour[nbtree[ch].nbor] = pos;
	  (void) memcpy ((char *)(nbtree+pos), 
			 (char *)(nbtree+ch), sizeof(neighbor));
	  pos = ch;
	}
	nbtree[pos].nbor = i;
	nbtree[pos].host = new_node;
	nbtree[pos].cost = cost;
	intour[i] = pos;
      }else{  /*---- already neighbor, update it if needed ------------*/
	if (nbtree[pos = intour[i]].cost > cost){
	  while ((ch=2*pos) < *last){
	    if (nbtree[ch].cost < nbtree[ch+1].cost)
	      ch++;
	    if (cost >= nbtree[ch].cost)
	      break;
	    intour[nbtree[ch].nbor] = pos;
	    (void) memcpy ((char *)(nbtree+pos),
			   			   (char *)(nbtree+ch), sizeof(neighbor));
	    pos = ch;
	  }
	  if (ch == *last){
	    if (cost < nbtree[ch].cost){
	      intour[nbtree[ch].nbor] = pos;
	      (void) memcpy ((char *)(nbtree+pos), 
			     (char *)(nbtree+ch), sizeof(neighbor));
	      pos=ch;
	    }
	  }
	  nbtree[pos].nbor = i;
	  nbtree[pos].host = new_node;
	  nbtree[pos].cost = cost;
	  intour[i] = pos;
	} /*---------- end if{ had to be updated } */
      } /*-------------- end if{ was not neighbor }else{ was neighbor} */
    } /*------------------ end if ('i' is not in the tour) */
  } /*---------------------- end for loop for all nodes */
}
