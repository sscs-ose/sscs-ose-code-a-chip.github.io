#include <math.h>
#include <memory.h>
#include <string.h>

#include "BB_macros.h"
#include "decomp.h"
#include "decomp_lower_bound.h"
#include "vrp_macros.h"
#include "my_decomp.h"
#include "sym_timemeas.h"
#include "sym_messages.h"
#include "network.h"
#include "vrp_sym_dg.h"

int vrp_decomp(int comp_num, double *compdensity)
{
   cg_prob *p = get_cg_ptr(NULL);
   LPdata *lp_data = p->dcmp_data.lp_data;
   cg_vrp_spec *vrp = (cg_vrp_spec *)(p->user);
   /* cut_gen_times *comp_times; */
   /* decomp_data *dcmp_data = &p->dcmp_data; */
   /*double *x = dcmp_data->x;*/
   int cuts_found = 0, init_cols, new_cols, termcode /*,*unbd_row*/ ;
   int cur_comp;
   network *n = vrp->n;
   edge **row_edges = (edge **) malloc((n->edgenum) * sizeof(edge *));
   int generated_all_columns = FALSE, generated_max_columns = FALSE; 
   int columns_deleted, *delstat = NULL;
   int stat, new_cuts;
    
   int i, prev_neighbor, v1, v2, count, vertnum = n->vertnum;
   elist *e,*e1, *neighbor_elist;
   vertex *verts = n->verts, *nv, *neighbor;
   double *new_demand = n->new_demand = (double *) calloc(vertnum, DSIZE);
   int total_demand = vrp->demand[0];
   int cap_check = vrp->capacity*(vrp->numroutes-1);
   int total_edge_cost;
   int verts_deleted = 0, edges_deleted = 0;
   double density_threshold = vrp->par.graph_density_threshold;

   int *compnodes = (int *) calloc(comp_num+1, ISIZE);
   int *compdemands = (int *) calloc(comp_num+1, ISIZE);
   
   if (vrp->par.decomp_decompose){
      connected(n, compnodes, compdemands, NULL, NULL, NULL);
   }else{
      for (i = 1; i < vertnum; i ++)
	 verts[i].comp = 1;
      compnodes[1] = vertnum - 1;
   }
   
   n->compnodes = compnodes; 

   /* find the edges that can be used to make 1-customer routes */
   if (vrp->par.allow_one_routes_in_bfm){
      for (e = verts[0].first; e; e = e->next_edge){
	 if (vrp->par.feasible_tours_only){
	    e->data->can_be_doubled = (total_demand - vrp->demand[e->other_end]
				       > cap_check) ? FALSE : TRUE;
	 }else{
	    e->data->can_be_doubled = TRUE;
	 }
      }
   }

   /*+ ((p->ub - p->cur_sol.objval > 5.5)? 170:0);*/

   /*Here, we are doing some preprocessing, but it is not needed for
     correctness and was causing problems for some reason, so I commented it
     out. Boy, I wish I had written some of this stuff down...*/
   
   /*FIRST, CONTRACT THE GRAPH */
   /* here we are contracting 1-chains into single edges: deleting intermediary
      nodes, adjusting elist objects for the endnodes of the chain, and keeping
      the pointers to the deleted edges in the corresponding elist->edges of
      the endnodes. However, if one endnode of 1-chain is depot, and the other
      is incident to it, we do not contract the intermediary node that is next
      to depot on the chain; failure to do this will result in multi-edge
      between the endnodes */
       
#if 0
   for(i = vertnum - 1, nv = verts + vertnum - 1; i; i--, nv--){

      if (nv->degree <= 2 || compdensity[nv->comp] > density_threshold)
	 continue;

#if 0
      not_incident_to_depot = TRUE;
      for (e = nv->first; e; e = e->next_edge){
	 if (!(e->other_end)){
	    not_incident_to_depot = FALSE;
	    break;
	 }
      }
#endif
      for (e = nv->first; e; e = e->next_edge){
	 if ((neighbor = e->other)->degree > 2 || neighbor->deleted ||
	     !neighbor->first->other_end || !neighbor->last->other_end)
	    continue;

	 prev_neighbor = i;
	 neighbor_elist = e; 
	 e->superlink = TRUE;
	 e->edgenum = 0;
	 total_edge_cost = 0;
	 e->edges = (edge **) calloc(vertnum, sizeof(edge *));
	 while(neighbor->degree == 2  && neighbor->first->other_end &&
	       neighbor->last->other_end){
	    /* trace the 1-chain */
	    e->edges[e->edgenum++] = neighbor_elist->data;
	    edges_deleted++; 
	    total_edge_cost += neighbor_elist->data->cost; 
	    new_demand[i] += neighbor->demand;
	    neighbor->deleted = TRUE;
	    verts_deleted++; 
	    v1 = neighbor->first->other_end;
	    v2 = neighbor->last->other_end;
	    
	    if (v1 == prev_neighbor){
	       prev_neighbor = neighbor->orignodenum;
	       neighbor_elist = neighbor->last;
	       neighbor = neighbor->last->other;
	    }else{
	       prev_neighbor = neighbor->orignodenum;
	       neighbor_elist = neighbor->first;
	       neighbor = neighbor->first->other;
	    }
	 }
	 e->edges[e->edgenum++] = neighbor_elist->data;
	 edges_deleted++;
	 total_edge_cost += neighbor_elist->data->cost;
	 e->data->cost = total_edge_cost;
	 e->other = neighbor;
	 e->other_end = neighbor->orignodenum;
	 for (e1=neighbor->first; e1; e1=e1->next_edge){
	    if (e1->other_end == prev_neighbor){
	       e1->data->other_data = e->data;
	       e1->data->cost = total_edge_cost;
	       e1->other = nv;
	       e1->other_end = nv->orignodenum;
	       e1->superlink = TRUE;
	       e1->edgenum = 0;
	       e1->edges = (edge **) calloc(vertnum, sizeof(edge *));
	       for (count = e->edgenum; count; count--) 
		  e1->edges[e1->edgenum++] = e->edges[count-1];
	    }
	 }
      }
   }

#if 0
   printf("Contracted graph: nodes %d, edges %d\n",
	  n->vertnum - verts_deleted, n->edgenum - edges_deleted);
#endif
   (void) used_time(&p->tt);
   /* for each component do */
#endif

   /*Here is where the real decomposition algorithm starts. each component of
     the support graph after removing the depot is decomposed separately since
     if there is a violated capacity constraint, then there is one using the
     nodes in just one of the components, i.e., we can consider each component
     separately. Now, it seems to me that at one time, I found a problem with
     this, too, and I added a parameter for whether to do decomposition
     component-wise or do the whole graph at once. the parameter is
     vrp->par.decomp_decompose. If set to FALSE, then it reats the whole graph
     as one component. I would stick with this for now. In that case, you can
     ignore the outer loop here. */
   
   for (cur_comp = 1; cur_comp <= comp_num; cur_comp++)
      if (compnodes[cur_comp]>3 && compdensity[cur_comp]<density_threshold){
	 printf("Calling decomp: density %.2f, obj %.2f, ub %.2f, level %d \n",
		compdensity[cur_comp], p->cur_sol.objval, p->ub,
		p->cur_sol.xlevel);
	 
	 /*Here we seed the matrix by generating a set of initial columns the
	 "conform" to the current LP solution by "brute force", i.e., through
	 depth first search of the fractional graph. There is a maximum time
	 to be spent in this routine, as well as a maximum number of columns
	 allowed to be generated in this way. If we get lucky and the
	 fractional graph is sparse, this may produce all possible columns
	 conforming to the current solution (indicated by setting
	 "generate_all_columns" to TRUE). Otherwise, we move on to the column
	 generation phase. */
	 
	 init_cols = vrp_create_initial_lp(p, n, cur_comp, comp_num,
					   compdemands, row_edges,
					   &generated_all_columns);
	 if (init_cols){
	    /* If we managed to find any columns, then check to see whether
	       we've already reached the maximum allowable. */
	    if (init_cols == lp_data->maxn){
	       generated_max_columns = TRUE;
	    }
	 }else if (generated_all_columns && vrp->par.generate_no_cols_cuts){
	    /*If no columns were found and the fractional graph was searched
              completey, then we can generate a "no columns cut" */
	    cuts_found += generate_no_cols_cut(p, lp_data, n, row_edges,
					       cur_comp);
	    printf("No columns cut generated\n");
	    continue;
	 }else{
	    /* Otherwise, try to generate columns */
	    new_cols = vrp_generate_new_cols(p, lp_data, n, row_edges,
					     cur_comp);
	    if (!new_cols){
	       /* If we still didn't find anything, then generate a no columns
                  cut*/
	       if (vrp->par.generate_no_cols_cuts){
		  cuts_found += generate_no_cols_cut(p, lp_data, n, row_edges,
						     cur_comp);
		  printf("No columns cut generated\n");
	       }
	       continue;
	    }
	 }
	 p->dcmp_data.timeout = time(NULL);
	 while(TRUE){
	    /* This is the main loop
	       1. Solve the current LP
	       2. If feasible, STOP.
	       3. Otherwise, try to generate columns.
	       4. Repeat
	    */
	    p->dcmp_data.iter_num++;
#if 0
	    /*Ignore this*/
	    comp_times = &p->comp_times;
	    comp_times->over_head += used_time(&p->tt);
	    
	    /*solve the current lp*/
	    if  (stat = CPXchecklp(lp_data->cpxenv,
				   (char *) "Decomp_prob", lp_data->n,
				   lp_data->m, 1, lp_data->obj,
				   lp_data->rhs, lp_data->sense,
				   lp_data->matbeg, lp_data->matcnt,
				   lp_data->matind, lp_data->matval,
				   lp_data->lb, lp_data->ub,
				   lp_data->rngval, lp_data->maxn +
				   lp_data->maxm, lp_data->maxm,
				   lp_data->maxnz+lp_data->maxm) ){
	       printf("#### AHHA  ###");
	    }
#endif
	    /*Solve the decomposition LP. Note that this all depends on CPLEX.
              I planned to remove that dependency, but never did. Shouldn't be
              too hard to do now that there is an interface to OSL. */
	    termcode = CPXdualopt(lp_data->cpxenv, lp_data->lp);
	    
	    switch (stat = CPXgetstat(lp_data->cpxenv,lp_data->lp)){
	     case CPX_OPTIMAL:              termcode = OPTIMAL; break;
	     case CPX_INFEASIBLE:           termcode = D_INFEASIBLE; break;
	     case CPX_UNBOUNDED:            termcode = D_UNBOUNDED; break;
	     case CPX_OBJ_LIM:              termcode = D_OBJLIM; break;
	     case CPX_IT_LIM_FEAS:
	     case CPX_IT_LIM_INFEAS:        termcode = D_ITLIM; break;
	     default:                       termcode = ABANDONED; break;
	    }
	    
	    /*comp_times->lp += used_time(&p->tt);*/
	    
	    switch (termcode){
	     case D_UNBOUNDED:
	       /*LP is infeasible. try to generate columns */
	       break;
	     case  OPTIMAL:
	       /*Found a decomposition. Try to generate cuts*/
	       cuts_found +=
		  (new_cuts = vrp_generate_cuts(p, n, cur_comp,
				 row_edges, vrp->par.generate_capacity_cuts));
	       printf("Decomp imposed %i new capacity constraints\n",
		      new_cuts);
	       break;
	     default:
	       printf("####CutGen: Unexpected lp termcode %i in decomp###\n\n",
		      termcode);
	       break;
	    }
	    if (termcode != D_UNBOUNDED || generated_all_columns
		                        || generated_max_columns){
	       printf("Generated %i columns\n", lp_data->n);
	       break;
	    }else if (time(NULL) - p->dcmp_data.timeout <
		      p->par.decomp_dynamic_timeout){
	       new_cols = vrp_generate_new_cols(p, lp_data, n, row_edges,
						cur_comp);
	    }else{
	       break;
	    }
	    switch (new_cols){
	     case 0:
	       /*This assumes an exact column generator*/
	       
	       /*If we're here, then the LP was infeasible and we couldn't
                 generate any new columns*/
	       
	       /*I think this line was for debugging (see below)*/
	       get_proof_of_infeas(lp_data, &i);

#if 0
	       /* This was some debugging I was trying to do. I figured out
                  the problem eventually (I think), but I left the code here.
                  Just ignore it. What was that bug...? It was really a nasty
                  one and not obvious at first. I'm not sure I fixed it
                  completely. I hope I remember ... */
	       termcode = CPXunloadprob(lp_data->cpxenv, lp_data->lp);
	       
	       lp_data->lp =
		  CPXloadlp(lp_data->cpxenv,
			    (char *) "Decomp_prob", lp_data->n, lp_data->m, 1,
			    lp_data->obj,
			    lp_data->rhs, lp_data->sense, lp_data->matbeg,
			    lp_data->matcnt, lp_data->matind, lp_data->matval,
			    lp_data->lb, lp_data->ub, lp_data->rngval,
			    lp_data->maxn+lp_data->maxm, lp_data->maxm,
			    lp_data->maxnz+lp_data->maxm);

	       termcode = CPXdualopt(lp_data->cpxenv, lp_data->lp);

	       get_proof_of_infeas(lp_data, &i);

	       new_cols = vrp_generate_new_cols(p, lp_data, n, row_edges,
						cur_comp);

	       if (new_cols > 0) break;
	       
	       switch (stat = CPXgetstat(lp_data->cpxenv,lp_data->lp)){
		case CPX_OPTIMAL:              termcode = OPTIMAL; break;
		case CPX_INFEASIBLE:           termcode = D_INFEASIBLE; break;
		case CPX_UNBOUNDED:            termcode = D_UNBOUNDED; break;
		case CPX_OBJ_LIM:              termcode = D_OBJLIM; break;
		case CPX_IT_LIM_FEAS:
		case CPX_IT_LIM_INFEAS:        termcode = D_ITLIM; break;
		default:                       termcode = ABANDONED; break;
	       }

	       MakeMPS(lp_data, 0, 0);
	       termcode = CPXwriteprob(lp_data->cpxenv, lp_data->lp,
			    "/home/tkr/tmp/matrices/bug.mps", "MPS");
#endif
	       /*Generate Farkas inequalities*/
	       if (vrp->par.generate_farkas_cuts){
		  cuts_found +=
		     (new_cuts = generate_farkas_cuts(p, lp_data, n,
						      row_edges, cur_comp));
		  printf("Generated %i FARKAS cuts\n", new_cuts);
	       }
	       if (!new_cols){
		  generated_all_columns = TRUE;
		  break;
	       }
	     case -1:
	       generated_max_columns = TRUE;
	       break;
	     default:
	       /*Generated some columns. Go back to the top and try to solve
                 the LP */
	       break;
	    }
	 }
	 /*For now, ignore all this. We can get into what all this is at a
           later point. Maybe you can figure it out, but it's difficult to
           explain.*/
	 if (generated_all_columns && !vrp->par.feasible_tours_only &&
	     p->par.decomp_dynamic_timeout == 0){
            delstat = (int *) calloc(lp_data->n, ISIZE);
            columns_deleted = purge_infeasible_cols(p, lp_data, row_edges,
						    delstat);
            if (columns_deleted == lp_data->n){
	       if (vrp->par.generate_no_cols_cuts){
		  cuts_found += generate_no_cols_cut(p, lp_data, n, row_edges,
						     cur_comp);
		  printf("No columns cut generated\n");
	       }
            }else{
	       lp_data->n -= columns_deleted;
	       CPXdelsetcols(lp_data->cpxenv, lp_data->lp, delstat);
	       termcode = CPXdualopt(lp_data->cpxenv, lp_data->lp);
	       
	       switch (stat = CPXgetstat(lp_data->cpxenv,lp_data->lp)){
	         case CPX_OPTIMAL:              termcode = OPTIMAL; break;
	         case CPX_INFEASIBLE:           termcode = D_INFEASIBLE; break;
		 case CPX_UNBOUNDED:            termcode = D_UNBOUNDED; break;
		 case CPX_OBJ_LIM:              termcode = D_OBJLIM; break;
		 case CPX_IT_LIM_FEAS:
		 case CPX_IT_LIM_INFEAS:        termcode = D_ITLIM; break;
		 default:                       termcode = ABANDONED; break;
	       }
	       
	       if (termcode==D_UNBOUNDED){
		  if (vrp->par.generate_farkas_cuts){
		     cuts_found +=
			(new_cuts = generate_farkas_cuts(p, lp_data, n,
							 row_edges, cur_comp));
		     printf("Generated %i FARKAS cuts\n", new_cuts);
		  }
	       }else{
		  if (lp_data->n != 1)
		     printf("###Unexpected lp termcode %i in decomp###\n\n",
			    termcode);  
	       }
	    }
	 }
	 /*CPXfreeprob(lp_data->cpxenv, &(lp_data->lp));*/ 
      }
   
   
   FREE(compnodes);
   FREE(compdemands);
   free(row_edges);
   free(new_demand);
   FREE(delstat);
   for (e=n->adjlist, i=0;i< 2*(n->edgenum) ;i++, e++)
      if (e->superlink) FREE(e->edges); 
   printf("Decomp imposed a total of %i new constraints\n", cuts_found);
   return(cuts_found);
   
}

/*===========================================================================*/

int vrp_create_initial_lp(cg_prob *p, network *n, int cur_comp, int num_comps,
			  int *compdemands, edge **row_edges,
			  int *generated_all_columns)
{
   
   LPdata *lp_data = p->dcmp_data.lp_data;
   int cpx_status, i;
   int *compnodes = n->compnodes;
   edge *edges = n->edges,  *temp_edge;
   vertex *verts = n->verts; 
   int v1, v0;  
   int edgenum = n->edgenum, node_num, row_num, low_tour_num, high_tour_num;
   cg_vrp_spec *vrp = (cg_vrp_spec *)(p->user);
   int size = vrp->vertnum + vrp->numroutes - 1;
   int *intour, *tour;
   edge **stack;
   elist *cur_edge;
   int numroutes = vrp->numroutes;
   int degree; /*partial degree of depot in the component */
   int position = 0;
   int minroutes_other_comps;
   double weight, weight_uncovered;
   int cost = MAXINT, num_edges_can_double = 0, total_demand = vrp->demand[0];
#ifdef NO_LIFTING
   int varnum = vrp->vertnum*(vrp->vertnum-1)/2;

   memset(lp_data->rhs, 0, varnum * DSIZE);
#endif
   
   /* find out how many nodes in the component; how many edges */
   node_num = compnodes[cur_comp]+1;
   row_num = 0;
   degree = 0;
     
   for (temp_edge = edges, i = 0; i < edgenum; i++, temp_edge++){
      v0 = temp_edge->v0;
      v1 = temp_edge->v1;
      if (verts[v0].comp == cur_comp || verts[v1].comp == cur_comp){
	 /* edge is in the component */
	 if (!(v0 && v1)) degree++;  /* edge is incident to depot */
	 if (temp_edge->can_be_doubled && !(verts[MAX(v0, v1)].deleted))
	    num_edges_can_double++;
#ifdef NO_LIFTING
	 temp_edge->row = INDEX(v0,v1);
	 row_edges[row_num++] = temp_edge;
	 lp_data->rhs[temp_edge->row] = temp_edge->weight;
      }
   }
   
   lp_data->rhs[varnum] = 1;
#else
	 temp_edge->row = row_num;
	 row_edges[row_num] = temp_edge;
	 lp_data->rhs[row_num++] = temp_edge->weight;
      }
   }
   
   lp_data->rhs[row_num++] = 1;
   lp_data->m = row_num;
#endif
   lp_data->nz = 0;
   lp_data->n = 0;

   if (p->par.decomp_initial_timeout <= 0){
      return(0);
   }

   low_tour_num = 1;
   high_tour_num = (vrp->par.allow_one_routes_in_bfm) ?
      (degree - num_edges_can_double)/2 + num_edges_can_double : degree/2;
   high_tour_num = MIN(high_tour_num, numroutes);
   if (vrp->par.feasible_tours_only){
      minroutes_other_comps =
	 BINS(total_demand - compdemands[cur_comp], vrp->capacity);
      high_tour_num = MIN(high_tour_num, numroutes - minroutes_other_comps);
      low_tour_num = BINS(compdemands[cur_comp], vrp->capacity);  
   }
   if (num_comps == 1) low_tour_num = high_tour_num = numroutes;
   
#if 0
   cost = vrp->par.feasible_tours_only ?
      p->ub - ceil(other_comps_cost) -.9999 : MAXINT; 
#endif
   
   intour = (int *) calloc(vrp->vertnum, sizeof(int));
   tour = (int *) calloc(size+1, sizeof(int));
   cur_edge = verts[0].first;
   stack = (edge **) malloc(verts[0].degree*sizeof(edge *));

#if 0
   while(cur_edge &&cur_edge->data->weight == 2 &&
	  verts[cur_edge->other_end].comp == cur_comp){
      intour[0]++;
      intour[cur_edge->other_end+numroutes]++;
      tour[count] = cur_edge->other_end+numroutes;
      tour[cur_edge->other_end+numroutes]=++count;
      cur_edge->data->deleted = 1;
      stack[position++] = cur_edge->data;
      cur_edge = cur_edge->next_edge;
      cost -= cur_edge->data->cost; 
   }
#endif
   weight = 0;
   weight_uncovered = compdemands[cur_comp];

   if (p->par.decomp_dynamic_timeout > 0){
      lp_data->maxn = 10;
   }

   p->dcmp_data.timeout = time(NULL);

   *generated_all_columns = bfm(p, 0, intour, tour, stack, position,
				low_tour_num, high_tour_num, cur_comp,
				&weight, &weight_uncovered, &cost);

   lp_data->maxn = vrp->par.max_num_columns;
#if 0   
   if (BINS(compdemands[cur_comp], vrp->capacity) +
       BINS(other_comps_demand, vrp->capacity) == vrp->numroutes){
      *generated_all_columns = bfm(p, 0, intour, tour, stack, position,
				   low_tour_num, high_tour_num, cur_comp,
				   &weight, &weight_uncovered, &cost);
   }else{  
      *generated_all_columns = 0;
   }
#endif
   
   if (*generated_all_columns){
      printf(" Time used : %ld \n", ( time(NULL) - p->dcmp_data.timeout));
#if 0
      fprintf(vrp->decomp_res," Time used : %d \n",
	      (time(NULL) - p->dcmp_data.timeout));
#endif
   }
   FREE(tour);
   FREE(intour);
   FREE(stack);
   
   if (!lp_data->n)
      return(0);
   lp_data->matbeg[lp_data->n]=lp_data->nz; 

   /*load_decomp_lp*/
   cpx_status = CPXsetintparam(lp_data->cpxenv, CPX_PARAM_SCAIND, -1);
   cpx_status =
      CPXsetintparam(lp_data->cpxenv, CPX_PARAM_BASINTERVAL, 2100000000);
   cpx_status = CPXsetintparam(lp_data->cpxenv, CPX_PARAM_AGGIND, 0);
   cpx_status = CPXsetintparam(lp_data->cpxenv, CPX_PARAM_DEPIND, 0);
   cpx_status = CPXsetintparam(lp_data->cpxenv, CPX_PARAM_PREIND, 0);
#if 0
   cpx_status = CPXsetintparam(lp_data->cpxenv, CPX_PARAM_REINV, 1);
#endif
   
   CPX_check_error("load_lp - CPXsetintparam");

   p->dcmp_data.iter_num = 0;

#if 0

   lp_data->lp = CPXcreateprob(lp_data->cpxenv, &cpx_status, "Decomp prob");

   cpx_status = CPXcopylp(lp_data->cpxenv, lp_data->lp, lp_data->n,
	                  lp_data->m, 1, lp_data->obj, lp_data->rhs,
	                  lp_data->sense, lp_data->matbeg, lp_data->matcnt,
	                  lp_data->matind, lp_data->matval, lp_data->lb,
	                  lp_data->ub, lp_data->rngval);
#endif   

   lp_data->lp =
      CPXloadlp(lp_data->cpxenv,
		(char *) "Decomp_prob", lp_data->n, lp_data->m, 1,
		lp_data->obj,
		lp_data->rhs, lp_data->sense, lp_data->matbeg, lp_data->matcnt,
		lp_data->matind, lp_data->matval, lp_data->lb, lp_data->ub,
		lp_data->rngval, lp_data->maxn+lp_data->maxm, lp_data->maxm,
		lp_data->maxnz+lp_data->maxm);

#if 0
   cpx_status = CPXchecklp(lp_data->cpxenv,
		(char *) "Decomp_prob", lp_data->n, lp_data->m, 1,
		lp_data->obj,
		lp_data->rhs, lp_data->sense, lp_data->matbeg, lp_data->matcnt,
		lp_data->matind, lp_data->matval, lp_data->lb, lp_data->ub,
		lp_data->rngval, lp_data->maxn+lp_data->maxm, lp_data->maxm,
		lp_data->maxnz+lp_data->maxm);
#endif   

   return(lp_data->n);
}

/*===========================================================================*/

int origind_compar(const void *origind1, const void *origind2)
{
   return((*((int *)origind1)) - (*((int *)origind2)));
}

/*===========================================================================*/
/*This is the brute force enumerator. Does depth-first search of the support
  graph. */

char bfm(cg_prob *p, int cur_node, int *intour, int *tour, edge **stack,
	 int position,int low_tour_num, int high_tour_num, int cur_comp,
	 double *weight, double *weight_uncovered, int *cost)
{
   cg_vrp_spec *vrp = (cg_vrp_spec *)(p->user);
   int numroutes = vrp->numroutes, vertnum = vrp->vertnum;
   vertex *verts = vrp->n->verts;
   int capacity = vrp->capacity;  
   int i, count=0;
   elist *cur_edge;
   edge *edge_data;
   int other_end;
   int *pt;
   double wt;
   double wt_un = 0;
   int cost_copy;
   int aux;
   double *new_demand =vrp->n->new_demand; 

   if (time(NULL) - p->dcmp_data.timeout > p->par.decomp_initial_timeout)
      return(FALSE);
   
   if (cur_node==0 && intour[0] >= low_tour_num && intour[0] <= high_tour_num){
      for (i = 0, pt = intour ; i < vertnum; i++){
	 if (*pt++==FALSE && (verts[i].comp==cur_comp) && !(verts[i].deleted))
	    break;
      }
      
      if (i == vertnum ){
#if 0          
	 printf("found a column\n");
	 j=0;
	 while( tour[j] ){
	    printf("%d ", (tour[j] > numroutes? tour[j]-numroutes:0));
	    j=tour[j];
	 }
	   
	 printf("\n");
#endif
	   
	 if (add_tour_to_col_set(p, tour, vrp, vrp->n->compnodes[cur_comp] + 1,
				 vrp->n)){
	    return(TRUE);
	 }else{
	    return(FALSE);
	 }
      }
      if (intour[0]==high_tour_num )
	 return(TRUE);
	 
      if (time(NULL) - p->dcmp_data.timeout > p->par.decomp_initial_timeout
	  /* || cols->num_cols == p->par.max_col_num_per_iter */)
	 return(FALSE);
     
   }
   
   
   wt = *weight;
   if (vrp->par.feasible_tours_only){
      if (!cur_node){
	 wt_un = *weight_uncovered;
	 *weight_uncovered -=wt;
	 *weight = 0;
      }else{
	 *weight=wt+verts[cur_node].demand+ new_demand[cur_node];
      }
      if ((cur_node) ? (*weight > capacity):
	  (BINS(*weight_uncovered, capacity) > high_tour_num - intour[0])){
	 *weight = wt;
	 if (!cur_node) *weight_uncovered = wt_un;
	 return(TRUE);
      }
   }
   cost_copy = *cost; 
   intour[cur_node]++;
   
   if (cur_node){
      for (cur_edge = verts[cur_node].first; cur_edge;
	   cur_edge = cur_edge->next_edge)
	 if (vrp->par.follow_one_edges && cur_edge->data->weight == 1){
	    other_end = cur_edge->other_end;
	    if ((!other_end)
		&& (!vrp->par.allow_one_routes_in_bfm || cur_edge->superlink
		    || !cur_edge->data->can_be_doubled)
		&& !(cur_node+numroutes == tour[intour[0]-1])){
	       /*we haven't arrived from the depot */
	       /* we got to go to depot now */ 
	       if (cur_edge->data->deleted){
		  intour[cur_node]--;
		  *weight = wt; 
		  return(TRUE);
	       }
	       
	       if ((aux = cost_copy - cur_edge->data->cost) < 0) {
		  intour[cur_node]--;
		  *weight = wt; 
		  return(TRUE);
	       }else{
		  *cost = aux;
	       }
	       
	       tour[cur_node+numroutes] = intour[0];
	       if (!bfm(p, other_end, intour, tour, stack, position,
			low_tour_num, high_tour_num, cur_comp, weight,
			weight_uncovered, cost)){
		  return(FALSE);
	       }else{
		  intour[cur_node]--;
		  *weight = wt;
		  *cost = cost_copy;
		  return(TRUE);
	       }

	    }
	    if (!(intour[other_end])){
	       if ((aux = cost_copy - cur_edge->data->cost) < 0) {
		  intour[cur_node]--;
		  *weight = wt; 
		  return(TRUE);
	       }else{
		  *cost = aux;
	       }
	       tour[cur_node+numroutes] = other_end + numroutes;
	       if (!bfm(p, other_end, intour, tour, stack, position,
			low_tour_num, high_tour_num, cur_comp, weight,
			weight_uncovered, cost)){
		  return(FALSE);
	       }else{
		  intour[cur_node]--;
		  *cost = cost_copy;
		  *weight = wt;
		  return(TRUE);
	       }
	    }
	 }else{
	    break;
	 }
	    
      for (cur_edge = verts[cur_node].first; cur_edge;
	   cur_edge = cur_edge->next_edge){
	 other_end = cur_edge->other_end;
         if (!(other_end ? intour[other_end] : cur_edge->data->deleted)){
	    if ((aux = cost_copy - cur_edge->data->cost) < 0) {
	       continue;
	    }else{
	       *cost = aux;
	    }
	    tour[cur_node+numroutes] = other_end ?
	       other_end + numroutes: intour[0];
	    if (!bfm(p, other_end, intour, tour, stack, position,
		     low_tour_num, high_tour_num, cur_comp, weight,
		     weight_uncovered, cost))
	       return(FALSE);
	 }
      }
	 
   }else{
      for (cur_edge = verts[cur_node].first; cur_edge;
	   cur_edge = cur_edge->next_edge){
	 other_end = cur_edge->other_end;
	 edge_data = cur_edge->data;
	 if (verts[other_end].comp == cur_comp && !(intour[other_end])
	     && !(edge_data->deleted)){
	    if ((aux = cost_copy - edge_data->cost) < 0) {
	       continue;
	    }else{
	       *cost = aux;
	    }

	    tour[intour[0]-1] = other_end + numroutes;
	    if (!vrp->par.allow_one_routes_in_bfm || cur_edge->superlink
		|| !cur_edge->data->can_be_doubled){
		edge_data->deleted = 1;
		if (cur_edge->superlink) edge_data->other_data->deleted = 1;
	    }
	    if (!bfm(p, other_end, intour, tour, stack, position,
		     low_tour_num, high_tour_num, cur_comp, weight,
		     weight_uncovered, cost))
	       return(FALSE);
	    edge_data->deleted= 1;
	    if (cur_edge->superlink) edge_data->other_data->deleted = 1;
	    stack[position++] = edge_data;
	    count++;
	 }
      }
      for (i = 0;i < count; i++){
	 (stack[--position])->deleted = 0;
	 if ((stack[position])->other_data)
	    (stack[position])->other_data->deleted = 0;
      }
      *weight_uncovered = wt_un;
   } 
   intour[cur_node]--;
   *weight=wt;
   *cost=cost_copy;
   return(TRUE);
   
}   

/*===========================================================================*/
/*This is called after fnding a feasible tour, i.e., a potential column, to
  chenge the tour into the column and add it to the column set. */

char add_tour_to_col_set(cg_prob *p, int *tour, cg_vrp_spec *vrp, int node_num,
			  network *net )
{  LPdata *lp_data = p->dcmp_data.lp_data;
   double *matval = lp_data->matval;
   int *matind = lp_data->matind;
   int num_routes = vrp->numroutes;
   int cur_node, next_node = 0, next_true_node, cur_true_node;
   int m, n, nz, node_count, count;   
   vertex *verts = net->verts;
   elist *e;
   int j;
   
   m = lp_data->m;
   n = lp_data->n;
   nz = lp_data->nz;
   count = 0;
   node_count = 0;
   cur_node=0;

   lp_data->lb[n] = 0;
   lp_data->ub[n] = CPX_INFBOUND;
   lp_data->obj[n] = 0;
   lp_data->matbeg[n] = nz;

 
   /* node_num is the number of nodes in the component +1, i.e, the depot */
   
   while (node_count < node_num - 1){
      cur_true_node = (cur_node > num_routes ) ? cur_node - num_routes : 0;
      if (cur_true_node) node_count++;
      if (node_count == node_num-1){
	 next_true_node = 0;
      }else{
	 next_node = tour[cur_node];
	 next_true_node = (next_node > num_routes) ? next_node - num_routes: 0;
      }
      
      for ( e = verts[cur_true_node].first; e; e = e->next_edge){
	 if (e->other_end == next_true_node){
	    if (!(e->superlink)){
	       if (nz && e->data->row == matind[nz-1]){
		  /* returning to depot immediately */
		  matval[nz-1] = 2;
		  break;
	       }else{
		  matval[nz] = 1;
		  matind[nz++] = e->data->row;
		  count++;
		  break;
	       }
	    }else{ /* we are following a 1-path */
	       for (j = 0; j < e->edgenum; j++){
		  matval[nz] = 1;
		  matind[nz++] = ((e->edges)[j])->row;
		  count++;
	       }
	       node_count += e->edgenum - 1; 
	       break;
	    }
	 }
      }
      cur_node = next_node;
   }
   /* take care of the last row */
   matval[nz] = 1;
   matind[nz++] = m - 1;
   count++;
      
   lp_data->nz = nz;
   lp_data->matcnt[n] = count;
   lp_data->n++;
   
   /* if (p->par.verbosity > 4 && vrp->dg_id)
      display_part_tour(vrp->dg_id, TRUE, (char *)"Partial Decomp Tour",
			tour, numroutes, CTOI_WAIT_FOR_CLICK_AND_REPORT);*/

   if (n == lp_data->maxn-1)
      return(FALSE); 
   else
      return(TRUE);
}

/*===========================================================================*/

void usr_open_decomp_lp(cg_prob *p, int varnum)
{
   cg_vrp_spec *vrp = (cg_vrp_spec *)(p->user);
   LPdata *lp_data;
   int maxn, maxm, maxnz, i;
   
   lp_data = p->dcmp_data.lp_data = (LPdata *) calloc (1, sizeof(LPdata));

#ifndef COMPILE_IN_CG
   open_lp_solver(lp_data);
#endif
   
   maxm = lp_data->maxm = lp_data->m = varnum + 1; 
   maxn = lp_data->maxn = vrp->par.max_num_columns;
   maxnz = lp_data->maxnz = lp_data->maxn*lp_data->maxm;

   lp_data->rhs    = (double *) calloc(maxm, sizeof(double));
   lp_data->sense  = (char *)   calloc(maxm, sizeof(char));
   lp_data->lb     = (double *) calloc(maxn + maxm, sizeof(double));
   lp_data->ub     = (double *) calloc(maxn + maxm, sizeof(double));
   lp_data->obj    = (double *) calloc(maxn + maxm, sizeof(double));
   lp_data->x      = (double *) calloc(maxn, sizeof(double));
   lp_data->matbeg = (int *)    calloc(maxn + maxm + 1, sizeof(int));
   lp_data->matval = (double *) calloc(maxnz + maxm, sizeof(double));
   lp_data->matind = (int *)    calloc(maxnz + maxm, sizeof(int));
   lp_data->matcnt = (int *)    calloc(maxn + maxm + 1, sizeof(int));
   lp_data->dj     = (double *) calloc(maxn, sizeof(int));

   /*p->dcmp_data.unbdd_row = (double *) calloc (maxm, sizeof(double)); */

   for (i = 0; i < maxm; i++)
      lp_data->sense[i] = 'E';

   lp_data->lp_is_modified = LP_HAS_NOT_BEEN_MODIFIED;
}   

/*===========================================================================*/
/*Try to generate cuts based on a decomposition */

int vrp_generate_cuts(cg_prob *p, network *n, int cur_comp, edge **row_edges,
		      int generate_cuts)
{
   LPdata *lp_data = p->dcmp_data.lp_data;
   double *x = lp_data->x;
   int i, num_cols = 0, pos_cols = 0;

   get_x(lp_data);
   
   for (i = 0; i < lp_data->n; i++){
      if (x[i] > 0){
	 pos_cols++;
	 if (generate_cuts)
	    num_cols += vrp_check_col(p, lp_data->matind + lp_data->matbeg[i],
				      lp_data->matval + lp_data->matbeg[i],
				      lp_data->matbeg[i+1] -
				      lp_data->matbeg[i] - 1, n,
				      cur_comp,row_edges );
	                           /* the last entry is the last row
				      is not an edge */
	 
      }
   }
   printf("There are %i columns at nonzero level\n", pos_cols);
   return(num_cols);
}

/*===========================================================================*/
/* Check a column to see if it violates any inequalities */

int vrp_check_col(cg_prob *p, int *colind, double *colval, int collen,
		   network *n, int cur_comp, edge **row_edges)
{
   cg_vrp_spec *vrp = (cg_vrp_spec *)p->user;
   int capacity = vrp->capacity, *demand = vrp->demand, vertnum = vrp->vertnum;
   int j,  weight = 0, reduced_weight, num_cuts = 0;
   double set_fract_weight = 0, reduced_fract_weight;
   double *new_demand = n->new_demand, *fract_weight; 
   int cut_size = (vrp->vertnum >> DELETE_POWER) +1;
   elist *e, *e1;
   vertex *verts = n->verts, *col_verts;
   int cur_vert = 0, next_vert, prev_vert, max_vert, vert1, vert2, *route;
   int cust_num = 0, reduced_cust_num;
   edge  *cur_edge, *true_edge;
   cut_data *new_cut;
   char *in_set;
   network *col_net;
   double lpetol = p->cur_sol.lpetol, max_val;

#ifndef NO_LIFTING
   int *new_ind = (int *) malloc(collen * ISIZE), i;

   for (i = 0; i < collen; i++)
      new_ind[i] = INDEX(row_edges[colind[i]]->v0, row_edges[colind[i]]->v1);
   col_net = createnet(new_ind, colval, collen, lpetol, vrp->edges, demand,
		       vertnum);
#else
   col_net = createnet(colind, colval, collen, lpetol, vrp->edges, demand,
		       vertnum);
#endif
   col_verts = col_net->verts;
   
   new_cut = (cut_data *) calloc(1, sizeof(cut_data));
   new_cut->size = cut_size;
   route = (int *) malloc(vertnum*ISIZE);
   in_set = (char *) calloc(vertnum, sizeof(char));
   fract_weight = (double *) malloc(vertnum * sizeof(double));
   new_cut->coef = malloc(cut_size);
   
   for (cur_vert = 0, e = col_verts[0].first; e; e = e->next_edge){
      if (e->data->scanned) continue;
      (cur_edge = e->data)->scanned = TRUE;
      cur_vert = prev_vert = 0;
      next_vert = cur_edge->v1;
      weight = cust_num = 0;
      set_fract_weight = 0;
      memset(new_cut->coef, 0, cut_size);
      memset(in_set, 0, vertnum);
      route[0] = next_vert;
      while(next_vert){
	 in_set[next_vert] = TRUE;
	 cust_num++;  
	 weight += demand[next_vert] + new_demand[next_vert];	
	 for (e1 = verts[next_vert].first; e1; e1 = e1->next_edge){
	    if (!(e1->superlink)){
	       if (in_set[e1->other_end]) set_fract_weight+= e1->data->weight;
	    }else{
	       true_edge = e1->edges[0];
	       if (in_set[(true_edge->v0 == next_vert) ?
			 true_edge->v1 : true_edge->v0])
		  set_fract_weight += e1->data->weight;
	    }
	    
	 }
	 new_cut->coef[next_vert >> DELETE_POWER] |=
	    (1 << (next_vert & DELETE_AND));
	 
	 if ((cust_num - set_fract_weight) < BINS(weight, capacity) - lpetol){
	    new_cut->type = (cust_num < vertnum/2 ?
			     SUBTOUR_ELIM_SIDE: SUBTOUR_ELIM_ACROSS);
	    new_cut->rhs = (new_cut->type ==SUBTOUR_ELIM_SIDE ?
			    RHS(cust_num, weight, capacity):
			    2*BINS(weight, capacity));
	    
	    num_cuts += cg_send_cut(new_cut);
	    vert1 = route[0];
	    reduced_fract_weight = set_fract_weight;
	    reduced_cust_num = cust_num;
	    reduced_weight = weight;
	    while(TRUE){
	       reduced_cust_num--;
	       reduced_weight -= demand[vert1] + new_demand[vert1];	
	       for (e1 = verts[vert1].first; e1; e1 = e1->next_edge){
		  if (!(e1->superlink)){
		     if (in_set[e1->other_end])
			reduced_fract_weight -= e1->data->weight;
		  }else{
		     true_edge = e1->edges[0];
		     if (in_set[(true_edge->v0 == next_vert) ?
			       true_edge->v1 : true_edge->v0])
			reduced_fract_weight -= e1->data->weight;
		  }
		  
	       }
	       
	       if ((reduced_cust_num - reduced_fract_weight) <
		   BINS(reduced_weight, capacity) -lpetol){
		  in_set[vert1] = FALSE;
		  new_cut->coef[vert1 >> DELETE_POWER] &=
		     ~(1 << (vert1 & DELETE_AND));
		  new_cut->type = (reduced_cust_num < vertnum/2 ?
				   SUBTOUR_ELIM_SIDE: SUBTOUR_ELIM_ACROSS);
		  new_cut->rhs = (new_cut->type ==SUBTOUR_ELIM_SIDE ?
				  RHS(reduced_cust_num, reduced_weight,
				      capacity):
				  2*BINS(reduced_weight, capacity));
		  
		  num_cuts += cg_send_cut(new_cut);
		  vert1 = route[vert1];
	       }else{
		  break;
	       }
	    }
	    vert2 = route[0];
	    while (vert2 != vert1){
	       in_set[vert2] = TRUE;
	       new_cut->coef[vert2 >> DELETE_POWER] |=
		  (1 << (vert2 & DELETE_AND));
	       vert2 = route[vert2];
	    }
	 }
	 prev_vert = cur_vert;
	 cur_vert = next_vert;
	 if (col_verts[cur_vert].first->other_end != prev_vert){
	    cur_edge = col_verts[cur_vert].first->data;
	    next_vert = col_verts[cur_vert].first->other_end;
	 }else{
	    cur_edge = col_verts[cur_vert].last->data; /*This statement could
						      possibly be taken out to
						      speed things up a bit*/
	    next_vert = col_verts[cur_vert].last->other_end;
	 }
	 route[cur_vert] = next_vert;
      }
      if (weight > capacity && !num_cuts){
	 cust_num = set_fract_weight = 0;
	 for (vert1 = route[0]; vert1; vert1 = route[vert1], cust_num = 0,
		 set_fract_weight = 0){
	    memset(new_cut->coef, 0, cut_size);
	    memset(fract_weight, 0, vertnum * DSIZE);
	    fract_weight[vert1] = -1.0;
	    new_cut->coef[vert1 >> DELETE_POWER] |=
	       (1 << (vert1 & DELETE_AND));
	    cust_num++;
	    for (e1 = verts[vert1].first; e1; e1 = e1->next_edge){
	       if (!(e1->superlink)){
		  if (in_set[e1->other_end]){
		     fract_weight[e1->other_end] = e1->data->weight;
		  }
	       }else{
		  true_edge = e1->edges[0];
		  if (in_set[(true_edge->v0 == next_vert) ?
			    true_edge->v1 : true_edge->v0]){
		     fract_weight[(true_edge->v0 == next_vert) ?
			    true_edge->v1 : true_edge->v0] = e1->data->weight;
		  }
	       }
	    }
	    weight = demand[vert1] + new_demand[vert1];
	    while(TRUE){ 
	       if ((cust_num - set_fract_weight) <
		   BINS(weight, capacity) - lpetol){
		  new_cut->type = (cust_num < vertnum/2 ?
				   SUBTOUR_ELIM_SIDE:SUBTOUR_ELIM_ACROSS);
		  new_cut->rhs =  (new_cut->type == SUBTOUR_ELIM_SIDE ?
				   RHS(cust_num, weight, capacity):
				   2*BINS(weight, capacity));
		  num_cuts += cg_send_cut(new_cut);
	       } 
	       for (max_val = 0, j = 1; j < vertnum; j++){
		  if (fract_weight[j] > max_val){
		     max_val = fract_weight[j];
		     max_vert = j; 
		  }
	       }
	       if (max_val > 0){    /* add the vertex to the set */
		  new_cut->coef[max_vert >> DELETE_POWER] |=
		     (1 << (max_vert & DELETE_AND));
		  cust_num++;
		  weight += demand[max_vert] + new_demand[max_vert];
		  set_fract_weight += fract_weight[max_vert];
		  fract_weight[max_vert] = -1.0;
		  for (e1 = verts[max_vert].first; e1; e1 = e1->next_edge){
		     if (!(e1->superlink)){
			if (in_set[e1->other_end] &&
			    fract_weight[e1->other_end] >= 0){
			   fract_weight[e1->other_end] += e1->data->weight;
			}
		     }else{
			true_edge = e1->edges[0];
			if (in_set[(true_edge->v0 == next_vert) ?
				  true_edge->v1 : true_edge->v0] &&
			    fract_weight[(true_edge->v0 == next_vert) ?
				  true_edge->v1 : true_edge->v0] >= 0){
			   fract_weight[(true_edge->v0 == next_vert) ?
				  true_edge->v1 : true_edge->v0] +=
			      e1->data->weight;
			}
		     }
		  }
	       }else{ /* can't add anything to the set */
		  break;
	       }
	    }
	 }
      }
      cur_edge->scanned = TRUE;
   }
   FREE(in_set);
   FREE(new_cut->coef);
   FREE(new_cut);
   return(num_cuts);
}

/*===========================================================================*/

#if 0
int vrp_check_col(cg_prob *p, int *colind, double *colval, int collen,
		   network *n, int cur_comp, edge **row_edges)
{
   cg_vrp_spec *vrp = (cg_vrp_spec *)p->user;
   int capacity = vrp->capacity, *demand = vrp->demand, vertnum = vrp->vertnum;
   int i, j,  weight = 0, reduced_weight, num_cuts = 0;
   double set_fract_weight = 0, reduced_fract_weight;
   double *new_demand = n->new_demand, *fract_weight; 
   int cut_size = (vrp->vertnum >> DELETE_POWER) +1;
   elist *e, *e1;
   vertex *verts = n->verts, *col_verts;
   int cur_vert = 0, next_vert, prev_vert, max_vert, vert1, vert2, *route;
   int cust_num = 0, reduced_cust_num, *new_ind;
   edge  *cur_edge, *true_edge;
   cut_data *new_cut;
   char *in_set;
   network *col_net;
   double lpetol = p->cur_sol.lpetol, max_val;

   new_ind = (int *) malloc(collen * ISIZE);
   for (i = 0; i < collen; i++)
      new_ind[i] = INDEX(row_edges[colind[i]]->v0, row_edges[colind[i]]->v1);
   col_net = createnet(new_ind, colval, collen, lpetol, vrp->edges, demand,
		       vertnum);
   col_verts = col_net->verts;
   
   new_cut = (cut_data *) calloc(1, sizeof(cut_data));
   new_cut->size = cut_size;
   route = (int *) malloc(vertnum*ISIZE);
   in_set = (char *) calloc(vertnum, sizeof(char));
   fract_weight = (double *) malloc(vertnum * sizeof(double));
   new_cut->coef = malloc(cut_size);
   
   for (cur_vert = 0, e = col_verts[0].first; e; e = e->next_edge){
      if (e->data->scanned) continue;
      (cur_edge = e->data)->scanned = TRUE;
      cur_vert = prev_vert = 0;
      next_vert = cur_edge->v1;
      weight = cust_num = 0;
      memset(in_set, 0, vertnum);
      route[0] = next_vert;
      while(next_vert){
	 in_set[next_vert] = TRUE;
	 cust_num++;  
	 weight += demand[next_vert] + new_demand[next_vert];	
	 prev_vert = cur_vert;
	 cur_vert = next_vert;
	 if (col_verts[cur_vert].first->other_end != prev_vert){
	    cur_edge = col_verts[cur_vert].first->data;
	    next_vert = col_verts[cur_vert].first->other_end;
	 }else{
	    cur_edge = col_verts[cur_vert].last->data; /*This statement could
						      possibly be taken out to
						      speed things up a bit*/
	    next_vert = col_verts[cur_vert].last->other_end;
	 }
	 route[cur_vert] = next_vert;
      }
      if (weight > capacity){
	 cust_num = set_fract_weight = 0;
	 for (vert1 = route[0]; vert1; vert1 = route[vert1], cust_num = 0,
		 set_fract_weight = 0){
	    memset(new_cut->coef, 0, cut_size);
	    memset(fract_weight, 0, vertnum * DSIZE);
	    fract_weight[vert1] = -1.0;
	    new_cut->coef[vert1 >> DELETE_POWER] |=
	       (1 << (vert1 & DELETE_AND));
	    cust_num++;
	    for (e1 = verts[vert1].first; e1; e1 = e1->next_edge){
	       if (!(e1->superlink)){
		  if (in_set[e1->other_end]){
		     fract_weight[e1->other_end] = e1->data->weight;
		  }
	       }else{
		  true_edge = e1->edges[0];
		  if (in_set[(true_edge->v0 == next_vert) ?
			    true_edge->v1 : true_edge->v0]){
		     fract_weight[(true_edge->v0 == next_vert) ?
			    true_edge->v1 : true_edge->v0] = e1->data->weight;
		  }
	       }
	    }
	    weight = demand[vert1] + new_demand[vert1];
	    while(TRUE){ 
	       if ((cust_num - set_fract_weight) <
		   BINS(weight, capacity) - lpetol){
		  new_cut->type = (cust_num < vertnum/2 ?
				   SUBTOUR_ELIM_SIDE:SUBTOUR_ELIM_ACROSS);
		  new_cut->rhs =  (new_cut->type == SUBTOUR_ELIM_SIDE ?
				   RHS(cust_num, weight, capacity):
				   2*BINS(weight, capacity));
		  num_cuts += cg_send_cut(new_cut);
	       } 
	       for (max_val = 0, j = 1; j < vertnum; j++){
		  if (fract_weight[j] > max_val){
		     max_val = fract_weight[j];
		     max_vert = j; 
		  }
	       }
	       if (max_val > 0){    /* add the vertex to the set */
		  new_cut->coef[max_vert >> DELETE_POWER] |=
		     (1 << (max_vert & DELETE_AND));
		  cust_num++;
		  weight += demand[max_vert] + new_demand[max_vert];
		  set_fract_weight += fract_weight[max_vert];
		  fract_weight[max_vert] = -1.0;
		  for (e1 = verts[max_vert].first; e1; e1 = e1->next_edge){
		     if (!(e1->superlink)){
			if (in_set[e1->other_end] &&
			    fract_weight[e1->other_end] >= 0){
			   fract_weight[e1->other_end] += e1->data->weight;
			}
		     }else{
			true_edge = e1->edges[0];
			if (in_set[(true_edge->v0 == next_vert) ?
				  true_edge->v1 : true_edge->v0] &&
			    fract_weight[(true_edge->v0 == next_vert) ?
				  true_edge->v1 : true_edge->v0] >= 0){
			   fract_weight[(true_edge->v0 == next_vert) ?
				  true_edge->v1 : true_edge->v0] +=
			      e1->data->weight;
			}
		     }
		  }
	       }else{ /* can't add anything to the set */
		  break;
	       }
	    }
	 }
      }	 
      cur_edge->scanned = TRUE;
   }
   FREE(in_set);
   FREE(new_cut->coef);
   FREE(new_cut);
   return(num_cuts);
}
#endif

/*===========================================================================*/

#if 0
int find_sets(double set_fract_weight, int cust_num, char *in_set, int *route,
	      int vert, int num_cuts, int capacity, int *demand,
	      int *new_demand, int weight, double lpetol, cut_data *new_cut,
	      int vertnum, vertex* verts)
{
   int next_vert = route[vert];
   int vert1;
   elist *e;
   edge *true_edge;
   double temp_fract_weight = 0;

   if (!next_vert) return(num_cuts);
   
   in_set[next_vert] = TRUE;
   cust_num++;
   weight += demand[next_vert] + new_demand[next_vert];
   new_cut->coef[next_vert >> DELETE_POWER] |=
      (1 << (next_vert & DELETE_AND));
   for (e = verts[next_vert].first; e; e = e->next_edge){
      if (!(e->superlink)){
	 if (in_set[e->other_end]){
	    temp_fract_weight += e->data->weight;
	 }
      }else{
	 true_edge = e->edges[0];
	 if (in_set[(true_edge->v0 == next_vert) ?
		   true_edge->v1 : true_edge->v0]){
	    temp_fract_weight += e->data->weight;
	 }
      }
   }
   set_fract_weight += temp_fract_weight;
   if ((cust_num - set_fract_weight) <
       BINS(weight, capacity) - lpetol){
      new_cut->type = (cust_num < vertnum/2 ?
		       SUBTOUR_ELIM_SIDE:SUBTOUR_ELIM_ACROSS);
      new_cut->rhs =  (new_cut->type == SUBTOUR_ELIM_SIDE ?
		       RHS(cust_num, weight, capacity):
		       2*BINS(weight, capacity));
      num_cuts += cg_send_cut(new_cut);
   } 
   num_cuts = find_sets(set_fract_weight, cust_num, in_set, route, next_vert,
			 num_cuts, capacity, demand, new_demand, weight,
			 lpetol, new_cut, vertnum, verts);
   in_set[next_vert] = FALSE;
   cust_num--;
   weight -= demand[next_vert] + new_demand[next_vert];
   set_fract_weight -= temp_fract_weight;
   new_cut->coef[next_vert >> DELETE_POWER] &=
      ~(1 << (next_vert & DELETE_AND));
   num_cuts = find_sets(set_fract_weight, cust_num, in_set, route, next_vert,
			 num_cuts, capacity, demand, new_demand, weight,
			 lpetol, new_cut, vertnum, verts);
   return(num_cuts);
}

/*===========================================================================*/

int vrp_check_col(cg_prob *p, int *colind, double *colval, int collen,
		   network *n, int cur_comp, edge **row_edges)
{
   cg_vrp_spec *vrp = (cg_vrp_spec *)p->user;
   int capacity = vrp->capacity, *demand = vrp->demand, vertnum = vrp->vertnum;
   int i, j,  weight = 0, reduced_weight, num_cuts = 0;
   double set_fract_weight = 0, reduced_fract_weight;
   double *new_demand = n->new_demand, *fract_weight; 
   int cut_size = (vrp->vertnum >> DELETE_POWER) +1;
   elist *e, *e1;
   vertex *verts = n->verts, *col_verts;
   int cur_vert = 0, next_vert, prev_vert, max_vert, vert1, vert2, *route;
   int cust_num = 0, reduced_cust_num, *new_ind;
   edge  *cur_edge, *true_edge;
   cut_data *new_cut;
   char *in_set;
   network *col_net;
   double lpetol = p->cur_sol.lpetol, max_val;

   new_ind = (int *) malloc(collen * ISIZE);
   for (i = 0; i < collen; i++)
      new_ind[i] = INDEX(row_edges[colind[i]]->v0, row_edges[colind[i]]->v1);
   col_net = createnet(new_ind, colval, collen, lpetol, vrp->edges, demand,
		       vertnum);
   col_verts = col_net->verts;
   
   new_cut = (cut_data *) calloc(1, sizeof(cut_data));
   new_cut->size = cut_size;
   route = (int *) malloc(vertnum*ISIZE);
   in_set = (char *) calloc(vertnum, sizeof(char));
   fract_weight = (double *) malloc(vertnum * sizeof(double));
   new_cut->coef = calloc(cut_size, CSIZE);
   
   for (cur_vert = 0, e = col_verts[0].first; e; e = e->next_edge){
      if (e->data->scanned) continue;
      (cur_edge = e->data)->scanned = TRUE;
      cur_vert = prev_vert = 0;
      next_vert = cur_edge->v1;
      weight = cust_num = 0;
      memset(in_set, 0, vertnum);
      route[0] = next_vert;
      while(next_vert){
	 in_set[next_vert] = TRUE;
	 cust_num++;  
	 weight += demand[next_vert] + new_demand[next_vert];	
	 prev_vert = cur_vert;
	 cur_vert = next_vert;
	 if (col_verts[cur_vert].first->other_end != prev_vert){
	    cur_edge = col_verts[cur_vert].first->data;
	    next_vert = col_verts[cur_vert].first->other_end;
	 }else{
	    cur_edge = col_verts[cur_vert].last->data; /*This statement could
						      possibly be taken out to
						      speed things up a bit*/
	    next_vert = col_verts[cur_vert].last->other_end;
	 }
	 route[cur_vert] = next_vert;
      }
      memset(in_set, 0, vertnum);
      if (weight > capacity){
	 num_cuts += find_sets(0, 0, in_set, route, 0, 0, capacity, demand,
			       new_demand, 0, lpetol, new_cut, vertnum,
			       verts);
      }
   }
   return(num_cuts);
}

#endif
	    
/*===========================================================================*/

#if 0

int vrp_check_col(cg_prob *p, int *colind, double *colval, int collen,
		   network *n, int cur_comp, edge **row_edges)
{
   cg_vrp_spec *vrp = (cg_vrp_spec *)p->user;
   int capacity = vrp->capacity, *demand = vrp->demand, vertnum = vrp->vertnum;
   int i, j,  weight = 0, reduced_weight, num_cuts = 0;
   double fract_weight = 0, reduced_fract_weight, *new_demand = n->new_demand; 
   int cut_size = (vrp->vertnum >> DELETE_POWER) +1;
   elist *e;
   vertex *verts = n->verts;
   int cur_vert = 0, next_vert, vert1, vert2, *route;
   int cust_num = 0, reduced_cust_num;
   edge  *cur_edge, *true_edge;
   cut_data *new_cut;
   char *in_set;

   new_cut = (cut_data *) calloc(1, sizeof(cut_data));
   new_cut->size = cut_size;
   route = (int *) malloc(vertnum*ISIZE);
   in_set = (char *) calloc(vertnum, sizeof(char));
   new_cut->coef = malloc(cut_size);
   
   for (i = 0; i < collen; i++){
      if (colval[i]==2) continue ;
      /* if the edge makes a one-customer route, ignore it */ 
      if (!cur_vert){
	 /* start a new route */
	 weight = cust_num = 0;
	 fract_weight = 0;
	 memset(new_cut->coef, 0, cut_size);
	 memset(in_set, 0, vertnum);
      }
      cur_edge = row_edges[colind[i]];
      next_vert = ((cur_vert == cur_edge->v0) ? cur_edge->v1 : cur_edge->v0);
      route[cur_vert] = next_vert;
      if (!next_vert){
	 cur_vert = 0; 
	 continue; 
      }
      in_set[next_vert] = TRUE;
      cust_num++;  
      weight += demand[next_vert] + new_demand[next_vert];	
      for (e = verts[next_vert].first; e; e = e->next_edge){
	 if (!(e->superlink)){
	    if (in_set[e->other_end]) fract_weight+= e->data->weight;
	 }else{
	    true_edge = e->edges[0];
	    if (in_set[(true_edge->v0 == next_vert) ?
		      true_edge->v1 : true_edge->v0])
	       fract_weight += e->data->weight;
	 }
	 
      }
      new_cut->coef[next_vert >> DELETE_POWER] |=
	 (1 << (next_vert & DELETE_AND));

      if ((cust_num - fract_weight) < BINS(weight, capacity) ){
	 new_cut->type = (cust_num < vertnum/2 ?
			  SUBTOUR_ELIM_SIDE: SUBTOUR_ELIM_ACROSS);
	 new_cut->rhs = (new_cut->type ==SUBTOUR_ELIM_SIDE ?
			 RHS(cust_num, weight, capacity):
			 2*BINS(weight, capacity));
	 
	 num_cuts += cg_send_cut(new_cut);
	 vert1 = route[0];
	 reduced_fract_weight = fract_weight;
	 reduced_cust_num = cust_num;
	 reduced_weight = weight;
	 while(TRUE){
	    reduced_cust_num--;
	    reduced_weight -= demand[vert1] + new_demand[vert1];	
	    for (e = verts[vert1].first; e; e = e->next_edge){
	       if (!(e->superlink)){
		  if (in_set[e->other_end])
		     reduced_fract_weight -= e->data->weight;
	       }else{
		  true_edge = e->edges[0];
		  if (in_set[(true_edge->v0 == next_vert) ?
			    true_edge->v1 : true_edge->v0])
		     reduced_fract_weight -= e->data->weight;
	       }
	       
	    }
	    
	    if ((reduced_cust_num - reduced_fract_weight) <
		BINS(reduced_weight, capacity) ){
	       in_set[vert1] = FALSE;
	       new_cut->coef[vert1 >> DELETE_POWER] &=
		  ~(1 << (vert1 & DELETE_AND));
	       new_cut->type = (reduced_cust_num < vertnum/2 ?
				SUBTOUR_ELIM_SIDE: SUBTOUR_ELIM_ACROSS);
	       new_cut->rhs = (new_cut->type ==SUBTOUR_ELIM_SIDE ?
			       RHS(reduced_cust_num, reduced_weight, capacity):
			       2*BINS(reduced_weight, capacity));
	       
	       num_cuts += cg_send_cut(new_cut);
	       vert1 = route[vert1];
	    }else{
	       break;
	    }
	 }
	 vert2 = route[0];
	 while (vert2 != vert1){
	    in_set[vert2] = TRUE;
	    new_cut->coef[vert2 >> DELETE_POWER] |=
	       (1 << (vert2 & DELETE_AND));
	    vert2 = route[vert2];
	 }
      }
      cur_vert = next_vert;
   }
   FREE(in_set);
   FREE(new_cut->coef);
   FREE(new_cut);
   return(num_cuts);
}

#endif

/*===========================================================================*/
/*There are several different version of this routine depending on how the lifting of the Farkas inequalities is done */

#ifdef FARKAS_LIFT_SEQUENTIAL

int generate_farkas_cuts(cg_prob *p, LPdata *lp_data, network *n,
			 edge **row_edges, int comp_num)
{
   cg_vrp_spec *vrp = (cg_vrp_spec *)p->user;
   double *unbd_row;
   int unbd_row_index, mult; 
   int i, j, k, num_arcs, equality, num_cuts = 0;
   int vertnum = vrp->vertnum, v0, v1, index, adjust; 
   int *arcs, *head, *nonzeros, *sort_order;
   double alpha, beta; 
   double *weights, *z, *soln;
   vertex *verts = n->verts;
   edge *cur_edge; 
   char *coef, *indicators;
   double etol = p->cur_sol.lpetol, viol; 
   cut_data *new_cut;
   double *costs;
#ifdef COMPILE_IN_CG
   lp_prob *lp = get_lp_ptr(NULL);
   LPdata *lp_data2 = lp->lp_data;
   char *status = lp_data2->status;
#endif
   
   display_support_graph(vrp->dg_id, TRUE, "fractional graph",
			 p->cur_sol.xlength, p->cur_sol.xind, p->cur_sol.xval,
			 p->cur_sol.lpetol, FALSE);
  
   num_arcs = lp_data->m - 1;
      
   z = (double *) calloc( MAX(lp_data->m, lp_data->n), DSIZE);
   soln = (double *) calloc(lp_data->m, DSIZE);
   head = (int *) calloc(lp_data->m, ISIZE);
   unbd_row = (double *) malloc(lp_data->m * DSIZE);
   new_cut = (cut_data *) calloc(1, sizeof(cut_data));
   arcs = (int *) malloc(num_arcs * ISIZE);
   indicators = (char *) calloc(num_arcs, sizeof(char));
   weights = (double *) malloc(vertnum*(vertnum - 1)/2 * DSIZE);
   nonzeros = (int *) malloc(vertnum*(vertnum - 1)/2 * ISIZE);
   
   new_cut->type = GENERAL_NONZEROS;
   new_cut->sense = 'G';
   new_cut->branch = DO_NOT_BRANCH_ON_THIS_ROW;
   new_cut->name = CUT__DO_NOT_SEND_TO_CP;

   /* SETTING the coef, num_arcs, arcs  */
   for (i = 0; i < num_arcs; i++){
      cur_edge = row_edges[i];
      arcs[i] = INDEX(cur_edge->v0, cur_edge->v1);
      if (vrp->par.follow_one_edges &&
	  fabs(cur_edge->weight - 1.0) < etol && !(cur_edge->can_be_doubled)){
	 indicators[i] = TRUE;
      }
   }
   sort_order = (int *) malloc(num_arcs * ISIZE);
   for(i = 0; i < num_arcs; sort_order[i] = i++);
   qsortucb_ii(arcs, sort_order, num_arcs);
    
   CPXgetbhead(lp_data->cpxenv, lp_data->lp, head, soln);

   costs = (double *) malloc((vertnum*(vertnum-1)/2) * DSIZE);
   for (unbd_row_index = 0; unbd_row_index < lp_data->m; unbd_row_index++){
      if (soln[unbd_row_index] < -etol || (soln[unbd_row_index] > etol &&
					   head[unbd_row_index] < 0)){
	 mult = soln[unbd_row_index] < 0 ? 1 : -1;
	 CPXbinvarow(lp_data->cpxenv, lp_data->lp, unbd_row_index, z);
	 for (i = 0, equality = 0; i < lp_data->n; i++){
	    if (mult*z[i] < -etol) break;
	    if (fabs(z[i]) < etol) equality++;
	 }
	 if (i < lp_data->n) continue;

	 CPXbinvrow(lp_data->cpxenv, lp_data->lp, unbd_row_index, unbd_row);

	 if (fabs(unbd_row[lp_data->m - 1]) > etol){
	    beta = mult*unbd_row[lp_data->m-1];
	 }else{
	    beta = 0;
	 }
#if 0
	 for (bigM = -beta, nz = 0, i = 0; i < num_arcs; i++){
	    bigM += -MIN(mult*unbd_row[i], 0);
	    if (unbd_row[i] != 0) nz++;
	 }
#endif

	 memset((char *)costs, 0, vertnum*(vertnum-1)/2 * DSIZE);

	 for (adjust = 0, i = 0, v1 = 1; v1 < vertnum; v1++){
	    if (!(verts[v1].comp == comp_num)) continue;
	    for (v0 = 0; v0 < v1; v0++){
	       if (v0 && !(verts[v0].comp == comp_num)) continue;
	       index = INDEX(v0, v1);
	       if (i < num_arcs && arcs[i] == index){
		  if (indicators[sort_order[i]]){
		     costs[arcs[i]] = -100000;
		     adjust++;
		  }else{
		     if (fabs(unbd_row[sort_order[i]]) > etol)
			costs[arcs[i]] = mult*unbd_row[sort_order[i]];
		  }
		  i++;
	       }else{
		  costs[index] =
		     (double)((MAXINT)/(vrp->vertnum+vrp->numroutes-1));
	       }
	    }
	 }
	 
	 for (alpha = -beta, i = 0; i < num_arcs; i++){
	    if (indicators[i])
	       alpha -= mult*unbd_row[i];
	 }
	 for (j = 0, i = 0; i < num_arcs; i++){
#if defined(COMPILE_IN_CG) && 1
	    if (indicators[sort_order[i]] &&
		!(row_edges[sort_order[i]]->status & TEMP_FIXED_TO_UB) &&
		!(row_edges[sort_order[i]]->status & PERM_FIXED_TO_UB) &&
		!(row_edges[sort_order[i]]->status & VARIABLE_BRANCHED_ON)){
#else
	    if (indicators[sort_order[i]]){
#endif
	       costs[arcs[i]] =
		  (double)((MAXINT)/(vrp->vertnum+vrp->numroutes-1));
	       adjust--;
	       if (fabs(weights[j] = decomp_lower_bound(vrp, costs, NULL,
							adjust,1) - alpha)
		   > etol && weights[j] < MAXDOUBLE - alpha){
		  alpha += weights[j];
		  costs[arcs[i]] = weights[j];
		  nonzeros[j++] = arcs[i];
	       }else{
		  costs[arcs[i]] = 0;
	       }
#if 0
	       if ((weights[j] = decomp_lower_bound(vrp, costs, NULL, adjust,1)
		    - alpha) < - etol){
		  alpha += weights[j];
		  costs[arcs[i]] = weights[j];
		  nonzeros[j++] = arcs[i];
	       }else{
		  costs[arcs[i]] = 0;
		  if (weights[j] > etol && weights[j] < MAXDOUBLE - alpha)
		     printf("\n\nWarning: possible bad coefficient in farkas"
			    "cut %f\n\n", weights[j]);
	       }
#endif
	    }else{
	       if (fabs(weights[j] = mult*unbd_row[sort_order[i]]) > etol){
		  nonzeros[j++] = arcs[i];
	       }
	    }
	 }
	 for (i = 0, k = 0, v1 = 1; v1 < vertnum; v1++){
	    if (!(verts[v1].comp == comp_num)) continue;
	    for (v0 = 0; v0 < v1; v0++){
	       if (v0 && !(verts[v0].comp == comp_num)) continue;
	       index = INDEX(v0, v1);
	       if (i < num_arcs && arcs[i] == index){
		  i++;
		  continue;
	       }
#if defined(COMPILE_IN_CG) && 1
	       if (k < lp_data2->n){
		  while (lp_data2->vars[k]->userind < index){
		     k++;
		  }
		  if (lp_data2->vars[k]->userind > index){
		     continue;
		  }else if ((status[k] & TEMP_FIXED_TO_LB) ||
			    (status[k] & PERM_FIXED_TO_LB) ||
			    (status[k] & VARIABLE_BRANCHED_ON)){
		     k++;
		     continue;
		  }else{
		     k++;
		  }
	       }else{
		  break;
	       }
#endif
	       costs[index] = -100000;
	       if (fabs(weights[j] = alpha -
		       decomp_lower_bound(vrp, costs, NULL, 1, 1)) > etol &&
		   weights[j] > alpha - MAXDOUBLE){
		  costs[index] = weights[j];
		  nonzeros[j++] = index;
	       }else{
		  costs[index] = 0;
	       }
#if 0
	       if ((weights[j] = alpha -
		    decomp_lower_bound(vrp, costs, NULL, 1, 1)) > etol){
		  costs[index] = weights[j];
		  nonzeros[j++] = index;
	       }else{
		  costs[index] = 0;
		  if (weights[j] <= -etol && weights[j] > alpha - MAXDOUBLE)
		     printf("\n\nWarning: possible bad coefficient in farkas"
			    "cut %f\n\n", weights[j]);
	       }
	       costs[index] = 0;
#endif
	    }
	 }
	 new_cut->rhs = alpha;
	 if (alpha == 0){
	    printf( "FARKAS CUT RHS 0 \n" );
	 }

	 printf( "rhs = %f   \n", new_cut->rhs) ;
	 printf("%i columns in the problem\n", lp_data->n);
	 printf("%i columns satisfy the row at equality\n", equality);
	 printf("%i nonzero entries in the cut\n", j);
	 viol = 0;
	 for (i = 0; i < lp_data->m - 1; i++){
	    viol += mult*unbd_row[i] * row_edges[i]->weight;
	 }
	 viol += beta;
	 printf( " value of the b*x_star+beta: %f \n", viol);

	 /* Pack cut */
	 new_cut->size = ISIZE + j * (ISIZE + DSIZE);
	 new_cut->coef = coef = malloc(new_cut->size);
	 memcpy(coef, (char *)&j, ISIZE);
	 coef += ISIZE;
	 memcpy(coef, (char *)nonzeros, j * ISIZE);
	 coef += j * ISIZE;
	 memcpy(coef, (char *)weights, j * DSIZE);
	 cg_send_cut(new_cut);
	 FREE(new_cut->coef);
	 num_cuts++;
      }
   }

   FREE(costs);
   FREE(head);
   FREE(nonzeros);
   FREE(weights);
   FREE(arcs);
   FREE(sort_order);
   FREE(indicators);
   FREE(new_cut);
   FREE(unbd_row);
   FREE(soln);
   FREE(z);
      
   return(num_cuts);
}

/*===========================================================================*/

#elif defined(FARKAS_LIFT_NAIVE)

int generate_farkas_cuts(cg_prob *p, LPdata *lp_data, network *n,
			 edge **row_edges, int comp_num)
{
   cg_vrp_spec *vrp = (cg_vrp_spec *)p->user;
   double *unbd_row;
   int unbd_row_index, mult, num_fracs; 
   int i, k, v0, v1, index, num_arcs, nz, equality, num_cuts = 0;
   int vertnum = vrp->vertnum; 
   int *arcs, *head;
   double alpha, beta, bigM; 
   double *weights, *z, *soln;
   vertex *verts = n->verts;
   edge *cur_edge; 
   char *cpt, *coef, *indicators;
   double etol = p->cur_sol.lpetol, viol; 
   cut_data *new_cut;
   double *costs;
#ifdef COMPILE_IN_CG
   lp_prob *lp = get_lp_ptr(NULL);
   LPdata *lp_data2 = lp->lp_data;
   char *status = lp_data2->status;
#endif
  
   num_arcs = lp_data->m - 1;
   
   z = (double *) calloc( MAX(lp_data->m, lp_data->n), DSIZE);
   soln = (double *) calloc(lp_data->m, DSIZE);
   head = (int *) calloc(lp_data->m, ISIZE);
   unbd_row = (double *) malloc(lp_data->m * DSIZE);
   new_cut = (cut_data *) calloc(1, sizeof(cut_data));
   arcs = (int *) malloc(num_arcs * ISIZE);
   indicators = (char *) calloc(num_arcs, sizeof(char));
   weights = (double *) calloc(num_arcs, DSIZE);
   
   new_cut->type = FARKAS;
   new_cut->sense = 'G';
   new_cut->branch = DO_NOT_BRANCH_ON_THIS_ROW;
   new_cut->name = CUT__DO_NOT_SEND_TO_CP;

   /* SETTING the coef, num_arcs, arcs  */
   for (i = 0; i < num_arcs; i++){
      cur_edge = row_edges[i];
      arcs[i] = INDEX(cur_edge->v0, cur_edge->v1);
      if (fabs(cur_edge->weight - 1.0) < etol && !(cur_edge->can_be_doubled)){
	 indicators[i] = TRUE;
      }
   }
    
   CPXgetbhead(lp_data->cpxenv, lp_data->lp, head, soln);

   costs = (double *) malloc((vertnum*(vertnum-1)/2) * DSIZE);
   
   /* SETTING THE RHS, bigM, weights and sending cuts*/
   for (unbd_row_index = 0; unbd_row_index < lp_data->m; unbd_row_index++){
      if (soln[unbd_row_index] < -etol || (soln[unbd_row_index] > etol &&
					   head[unbd_row_index] < 0)){
	 mult = soln[unbd_row_index] < 0 ? 1 : -1;
	 CPXbinvarow(lp_data->cpxenv, lp_data->lp, unbd_row_index, z);
	 for (i = 0, equality = 0; i < lp_data->n; i++){
	    if (mult*z[i] < -etol) break;
	    if (fabs(z[i]) < etol) equality++;
	 }
	 if (i < lp_data->n) continue;
	 
	 CPXbinvrow(lp_data->cpxenv, lp_data->lp, unbd_row_index, unbd_row);

	 if (fabs(unbd_row[lp_data->m - 1]) > etol){
	    beta = mult*unbd_row[lp_data->m-1];
	 }else{
	    beta = 0;
	 }
#if 0
	 for (bigM = -beta, nz = 0, i = 0; i < num_arcs; i++){
	    bigM += -MIN(mult*unbd_row[i], 0);
	    if (unbd_row[i] != 0) nz++;
	 }
#endif

	 memset((char *)costs, 0, vertnum*(vertnum-1)/2 * DSIZE);

	 for (alpha = beta, bigM = 0, nz = 0, i = 0; i < lp_data->m - 1; i++){
	    if (!indicators[i]){
	       if (fabs(unbd_row[i]) > etol){
		  costs[arcs[i]] = mult*unbd_row[i];
		  nz++;
	       }
#if defined(COMPILE_IN_CG) && 1
	    }else if ((row_edges[i]->status & TEMP_FIXED_TO_UB)||
		      (row_edges[i]->status & PERM_FIXED_TO_UB) ||
		      (row_edges[i]->status & VARIABLE_BRANCHED_ON)){
	       costs[arcs[i]] = -100000;
#endif
	    }else if (fabs(unbd_row[i]) > etol){
	       alpha += mult*unbd_row[i];
	    }
	 }
#if defined(COMPILE_IN_CG) && 1
	 for (i = 0, k = 0, v1 = 1, index = 0; v1 < vertnum; v1++){
	    if (!(verts[v1].comp == comp_num)) continue;
	    for (v0 = 0; v0 < v1; v0++){
	       if (v0 && !(verts[v0].comp == comp_num)) continue;
	       index = INDEX(v0, v1);
	       if (i < num_arcs && arcs[i] == index){
		  i++;
		  continue;
	       }
	       if (k < lp_data2->n){
		  while (lp_data2->vars[k]->userind < index){
		     k++;
		  }
		  if (lp_data2->vars[k]->userind > index){
		     costs[index] =
			(double)((MAXINT)/(vrp->vertnum+vrp->numroutes-1));
		  }else if ((status[k] & TEMP_FIXED_TO_LB) ||
			    (status[k] & PERM_FIXED_TO_LB) ||
			    (status[k] & VARIABLE_BRANCHED_ON)){
		     costs[index] =
			(double)((MAXINT)/(vrp->vertnum+vrp->numroutes-1));
		     k++;
		  }else{
		     k++;
		  }
	       }else{
		  costs[index] =
		     (double)((MAXINT)/(vrp->vertnum+vrp->numroutes-1));
	       }
	    }
	 }
#endif
	 if ((bigM = -decomp_lower_bound(vrp, costs, NULL, 0, 1))==-MAXDOUBLE)
	     continue;
	 if (bigM > -etol && bigM < etol)
	    bigM = 0.0;
	 bigM -= alpha;
	 for (i = 0, num_fracs = 0; i < lp_data->m - 1; i++){
	    if (indicators[i]){
	       alpha += bigM;
	    }else if (fabs(unbd_row[i]) > etol){
	       weights[num_fracs++] = mult*unbd_row[i];
	    }else{
	       weights[num_fracs++] = 0;
	    }
	 }
	 new_cut->rhs = -alpha;
	 if (alpha == 0){
	    printf( "FARKAS CUT RHS 0 \n" );
	 }

	 printf( "bigM = %f  \n", bigM);
	 printf( "rhs = %f   \n", new_cut->rhs) ;
	 printf("%i columns in the problem\n", lp_data->n);
	 printf("%i columns satisfy the row at equality\n", equality);
	 printf("%i nonzero entries in the cut\n", nz);
	 viol = 0;
	 for (i = 0; i < lp_data->m - 1; i++){
	    viol += mult*unbd_row[i] * row_edges[i]->weight;
	 }
	 viol += beta;
	 printf( " value of the b*x_star+beta: %f \n", viol);

	 /* Pack cut */
	 new_cut->size = (vrp->vertnum >> DELETE_POWER) + 1 +
	    (num_arcs + 2) * ISIZE + num_arcs + (num_fracs + 1) * DSIZE;
	 new_cut->coef = coef = calloc(new_cut->size, sizeof(char));
	 for (i = 1; i < vertnum; i++)
	    if (verts[i].comp == comp_num)
	       coef[i >> DELETE_POWER] |= (1 << (i & DELETE_AND));	    
	 cpt = coef + ((vertnum >> DELETE_POWER) + 1);
	 memcpy(cpt, (char *)&num_arcs, ISIZE);
	 cpt += ISIZE;
	 memcpy(cpt, (char *)arcs, ISIZE*(num_arcs));
	 cpt += ISIZE * num_arcs;
	 memcpy(cpt, (char *)indicators, num_arcs);
	 cpt += num_arcs;
	 memcpy(cpt, (char *)&num_fracs, ISIZE);
	 cpt+= ISIZE;
	 memcpy(cpt, (char *)&bigM, DSIZE);
	 cpt+= DSIZE;
	 memcpy(cpt, (char *)weights, num_fracs*DSIZE);
	 cg_send_cut(new_cut);
	 FREE(new_cut->coef);
	 num_cuts++;
      }
   }

   FREE(costs);
   FREE(head);
   FREE(weights);
   FREE(arcs);
   FREE(indicators);
   FREE(new_cut);
   FREE(unbd_row);
   FREE(soln);
   FREE(z);
      
   return(num_cuts);
}

/*===========================================================================*/

#else

int generate_farkas_cuts(cg_prob *p, LPdata *lp_data, network *n,
			 edge **row_edges, int comp_num)
{
   cg_vrp_spec *vrp = (cg_vrp_spec *)p->user;
   double *unbd_row;
   int unbd_row_index, mult; 
   int i, nz, equality, num_cuts = 0;
   int vertnum = vrp->vertnum; 
   int *head, *nonzeros;
   double beta; 
   double *weights, *z, *soln;
   char *coef;
   double etol = p->cur_sol.lpetol; 
   cut_data *new_cut;
  
   z = (double *) calloc( MAX(lp_data->m, lp_data->n), DSIZE);
   soln = (double *) calloc(lp_data->m, DSIZE);
   head = (int *) calloc(lp_data->m, ISIZE);
   unbd_row = (double *) malloc(lp_data->m * DSIZE);
   new_cut = (cut_data *) calloc(1, sizeof(cut_data));
   weights = (double *) malloc(vertnum*(vertnum - 1)/2 * DSIZE);
   nonzeros = (int *) malloc(vertnum*(vertnum - 1)/2 * ISIZE);
   
   new_cut->type = GENERAL_NONZEROS;
   new_cut->sense = 'G';
   new_cut->branch = DO_NOT_BRANCH_ON_THIS_ROW;
   /*For now, we do not send these to the CP because they are only locally
     valid due to the fact that we use fixed variables to generate them.
     Right now, we can only do this if the LP is compiled in */
   new_cut->name = CUT__DO_NOT_SEND_TO_CP;
   
   CPXgetbhead(lp_data->cpxenv, lp_data->lp, head, soln);

   /* SETTING THE RHS, bigM, weights and sending cuts*/
   get_x(lp_data);
   for (unbd_row_index = 0; unbd_row_index < lp_data->m; unbd_row_index++){
      if (soln[unbd_row_index] < -etol || (soln[unbd_row_index] > etol &&
					   head[unbd_row_index] < 0)){
	 mult = soln[unbd_row_index] < 0 ? 1 : -1;
	 CPXbinvarow(lp_data->cpxenv, lp_data->lp, unbd_row_index, z);
	 for (i = 0, equality = 0; i < lp_data->n; i++){
	    if (mult*z[i] < -etol) break;
	    if (fabs(z[i]) < etol) equality++;
	 }
	 if (i < lp_data->n) continue;
	 
	 CPXbinvrow(lp_data->cpxenv, lp_data->lp, unbd_row_index, unbd_row);

	 if (fabs(unbd_row[lp_data->m - 1]) > etol){
	    beta = mult*unbd_row[lp_data->m-1];
	 }else{
	    beta = 0;
	 }

	 new_cut->rhs = beta;

	 for (i = nz = 0; i < lp_data->m - 1; i ++)
	    if (fabs(weights[nz] = mult*unbd_row[i]) > etol)
	       nonzeros[nz++] = i;
	 
	 printf( "rhs = %f   \n", new_cut->rhs) ;
	 printf("%i columns in the problem\n", lp_data->n);
	 printf("%i columns satisfy the row at equality\n", equality);
	 printf("%i nonzero entries in the cut\n", nz);

	 /* Pack cut */
	 new_cut->size = ISIZE + nz * (ISIZE + DSIZE);
	 new_cut->coef = coef = malloc(new_cut->size);
	 memcpy(coef, (char *)&nz, ISIZE);
	 coef += ISIZE;
	 memcpy(coef, (char *)nonzeros, nz * ISIZE);
	 coef += nz * ISIZE;
	 memcpy(coef, (char *)weights, nz * DSIZE);
	 cg_send_cut(new_cut);
	 FREE(new_cut->coef);
	 num_cuts++;
      }
   }

   FREE(head);
   FREE(weights);
   FREE(new_cut);
   FREE(unbd_row);
   FREE(soln);
   FREE(z);
      
   return(num_cuts);
}
#endif

/*===========================================================================*/

int generate_no_cols_cut(cg_prob *p,LPdata *lp_data , network *n,
                        edge **row_edges, int cur_comp)
{
   cg_vrp_spec *vrp = (cg_vrp_spec *)p->user;
   int i,num_arcs, cut_size, num_ones = 0, num_cuts = 0;
   int vertnum = vrp->vertnum; 
   int *arcs;
   char *indicators;
   vertex *verts = n->verts;
   edge *cur_edge; 
   char *cpt, *coef /*, *position */;
   double etol = p->cur_sol.lpetol; 
   cut_data *new_cut;
  
   num_arcs = n->edgenum;
   cut_size = (vrp->vertnum >> DELETE_POWER) + 1 + (num_arcs + 1) * ISIZE +
      num_arcs;
  
   new_cut = (cut_data *) calloc(1, sizeof(cut_data));
   new_cut->coef = coef = calloc(cut_size, sizeof(char));
   arcs = (int *) calloc(num_arcs, sizeof(int));
   indicators = (char *) calloc(num_arcs, sizeof(char));
   
   /* SETTING the coef,  arcs, values  */
   for (i = 0; i < num_arcs; i++){
      cur_edge = row_edges[i];
      arcs[i] = INDEX(cur_edge->v0, cur_edge->v1);
      if (fabs(cur_edge->weight - 1) < etol && !(cur_edge->can_be_doubled)){
	 indicators[i] = TRUE;
	 num_ones++;
      }
   }
#if 0
   printf("Here's the no columns cut:\n ");
   printf("Number of arcs %d , rhs  %d \n", num_arcs, num_ones-1);
   for (i = 0; i < num_arcs; i++)
      printf(" %d  %d  ;\n ",arcs[i], indicators[i]);
   printf("End no columns cut \n\n");
#endif
   /* Pack cut */
   new_cut->type = NO_COLUMNS;
   new_cut->sense = 'L';
   new_cut->size = cut_size;
   new_cut->branch = ALLOWED_TO_BRANCH_ON;
   new_cut->rhs = num_ones - 1.0;  

   for (i = 1; i < vertnum; i++)
      if (verts[i].comp == cur_comp)
	 coef[i >> DELETE_POWER] |= (1 << (i & DELETE_AND));	    
   cpt = coef + ((vertnum >> DELETE_POWER) + 1);
   memcpy(cpt, (char *)&num_arcs, ISIZE);
   cpt += ISIZE;
   memcpy(cpt, (char *)arcs, ISIZE * num_arcs);
   cpt += num_arcs * ISIZE;
   memcpy(cpt, indicators, num_arcs);

#if 0   
   /* send the no_cols_cut to CUT_POOL*/
   if (p->cur_sol.cp){
      int s_bufid, info, cnt=1;
      
      PVM_FUNC(s_bufid, pvm_initsend(PvmDataRaw));
      PVM_FUNC(info, pvm_pkint(&cnt, 1, 1));
      PVM_FUNC(info, pvm_pkint(&p->cur_sol.xlevel, 1, 1));
      pack_cut(new_cut);
      PVM_FUNC(info, pvm_send(p->cur_sol.cp, 601));
      PVM_FUNC(info, pvm_freebuf(s_bufid));
      PRINT(p->par.verbosity, 4, ("1 no_columns  cut sent to cutpool\n"));
   }
#endif
   num_cuts += cg_send_cut(new_cut);
   FREE(coef);
   FREE(new_cut);
   FREE(arcs);
   FREE(indicators);
   return(num_cuts);
}

/*===========================================================================*/

int purge_infeasible_cols(cg_prob *p, LPdata *lp_data,  edge **row_edges,
			  int *delstat)
{
   cg_vrp_spec *vrp = (cg_vrp_spec *)p->user;
   int capacity = vrp->capacity, set_demand = 0;
   int *demand = vrp->demand;
   double *new_demand = vrp->n->new_demand;
   int i, j, collen, *colind;
   double *colval;  
   int cur_vert, next_vert;
   edge  *cur_edge;
   int cols_deleted = 0; 
    
   for (j = 0; j < lp_data->n; j++){
     collen = lp_data->matcnt[j]-1;
     colval = lp_data->matval + lp_data->matbeg[j];
     colind = lp_data->matind + lp_data->matbeg[j];
	
     cur_vert = 0;
    
     for ( i = 0; i < collen; i++){
        if (colval[i] == 2) continue;
        /* if the edge makes a one-customer route, ignore it */ 
        if (!cur_vert) set_demand = 0;
	   /* start a new route */
	
        cur_edge = row_edges[colind[i]];
        next_vert = ((cur_vert == cur_edge->v0) ? cur_edge->v1 : cur_edge->v0);
        if (!next_vert){
	   cur_vert = 0; 
	   continue; 
        }
        set_demand += demand[next_vert] + new_demand[next_vert];
	if (set_demand > capacity){
	   delstat[j] = 1;
	   cols_deleted++;
	   break;
        }	
        cur_vert = next_vert;
     }
   }
   return(cols_deleted);
}

/*===========================================================================*/
/*This routine generates the new columns To do this, we need a proof of
  infeasibility in order to generate new columns. The proof is basically a
  Farkas inequality (row of B^{-1 }) that separates the current fractional
  solution from the convex hull of the current set of columns. We try to find
  a new column which violates this Farkas inequality by solving the relaxation
  with the left hand side of this inequality as the objective function. Again,
  there are different options based on different lifting methods. */

#ifndef NO_LIFTING

int vrp_generate_new_cols(cg_prob *p, LPdata *lp_data, network *n,
			  edge **row_edges, int comp_num)
{
   cg_vrp_spec *vrp = (cg_vrp_spec *)p->user;
   double *unbd_row;
   int unbd_row_index, mult; 
   int i, num_arcs, equality;
   int vertnum = vrp->vertnum, v0, v1, index; 
   int *arcs, *head, *sort_order;
   double alpha, beta; 
   double *z, *soln;
   vertex *verts = n->verts;
   edge *cur_edge; 
   char *indicators;
   double etol = p->cur_sol.lpetol; 
   double *costs, lb = 0.0, ub = 1.0, *matval, obj = 0.0;
   int matbeg[2] = {0,0};
   int *matind, *x, nzcnt = 0, coef, cpx_status;

   num_arcs = lp_data->m - 1;
      
   arcs = (int *) malloc(num_arcs * ISIZE);
   indicators = (char *) calloc(num_arcs, sizeof(char));
   /* SETTING the coef, num_arcs, arcs  */
   for (i = 0; i < num_arcs; i++){
      cur_edge = row_edges[i];
      arcs[i] = INDEX(cur_edge->v0, cur_edge->v1);
      if (vrp->par.follow_one_edges &&
	  fabs(cur_edge->weight - 1.0) < etol && !(cur_edge->can_be_doubled)){
	 indicators[i] = TRUE;
      }
   }
   sort_order = (int *) malloc(num_arcs * ISIZE);
   for(i = 0; i < num_arcs; sort_order[i] = i++);
   qsortucb_ii(arcs, sort_order, num_arcs);
    
   if (!lp_data->n){
      costs = (double *) calloc(vertnum*(vertnum-1)/2, DSIZE);
      x = (int *) calloc(vertnum*(vertnum-1)/2, ISIZE);
      for (i = 0, v1 = 1; v1 < vertnum; v1++){
	 if (!(verts[v1].comp == comp_num)) continue;
	 for (v0 = 0; v0 < v1; v0++){
	    if (v0 && !(verts[v0].comp == comp_num)) continue;
	    index = INDEX(v0, v1);
	    if (i < num_arcs && arcs[i] == index){
	       if (indicators[sort_order[i]]){
		  costs[arcs[i]] = -100000;
	       }
	       i++;
	    }else{
	       costs[index] =
		  (double)((MAXINT)/(vrp->vertnum+vrp->numroutes-1));
	    }
	 }
      }
      if (decomp_lower_bound(vrp, costs, x, 0, 1) == 0){
	 cpx_status = CPXsetintparam(lp_data->cpxenv, CPX_PARAM_SCAIND, -1);
	 cpx_status =
	    CPXsetintparam(lp_data->cpxenv, CPX_PARAM_BASINTERVAL, 2100000000);
	 cpx_status = CPXsetintparam(lp_data->cpxenv, CPX_PARAM_AGGIND, 0);
	 cpx_status = CPXsetintparam(lp_data->cpxenv, CPX_PARAM_DEPIND, 0);
	 cpx_status = CPXsetintparam(lp_data->cpxenv, CPX_PARAM_PREIND, 0);
	 
	 CPX_check_error("load_lp - CPXsetintparam");
	 
	 lp_data->lp =
	    CPXloadlp(lp_data->cpxenv,
		      (char *) "Decomp_prob", lp_data->n, lp_data->m, 1,
		      lp_data->obj,
		      lp_data->rhs, lp_data->sense, lp_data->matbeg,
		      lp_data->matcnt, lp_data->matind, lp_data->matval,
		      lp_data->lb, lp_data->ub, lp_data->rngval,
		      lp_data->maxn+lp_data->maxm, lp_data->maxm,
		      lp_data->maxnz+lp_data->maxm);

	 p->dcmp_data.iter_num = 0;
	 matind = (int *)    malloc((vrp->vertnum+vrp->numroutes)*ISIZE);
	 matval = (double *) malloc((vrp->vertnum+vrp->numroutes)*DSIZE);
	 for (nzcnt = 0, i = 0; i < num_arcs; i++){
	    cur_edge = row_edges[i];
	    if ((coef = x[INDEX(cur_edge->v0, cur_edge->v1)]) > etol){
	       matind[nzcnt] = i;
	       matval[nzcnt++] = (double)coef;
	    }
	 }
	 matind[nzcnt] = lp_data->m-1;
	 matval[nzcnt++] = 1.0;
	 if (nzcnt > vrp->vertnum+vrp->numroutes){
	    printf("Too many nonzeros (%i) !!!!\n\n", nzcnt);
	    sleep(600);
	    exit();
	 }
	 matbeg[1] = nzcnt;
	 if (lp_data->n < lp_data->maxn){
	    add_cols(lp_data, 1, nzcnt, &obj, matbeg, matind, matval, &lb,
		     &ub, 0);
	    lp_data->matbeg[lp_data->n] = lp_data->nz;
	 }
	 FREE(arcs);
	 FREE(indicators);
	 FREE(costs);
	 FREE(x);
	 FREE(matval);
	 FREE(matind);
	 return(lp_data->n == lp_data->maxn ? -1 : 1);
      }else{
	 FREE(arcs);
	 FREE(indicators);
	 return(0);
      }
   }
   
   x = (int *) calloc(vertnum*(vertnum-1)/2, ISIZE);
   z = (double *) calloc( MAX(lp_data->m, lp_data->n), DSIZE);
   soln = (double *) calloc(lp_data->m, DSIZE);
   head = (int *) calloc(lp_data->m, ISIZE);
   unbd_row = (double *) malloc(lp_data->m * DSIZE);
   
   CPXgetbhead(lp_data->cpxenv, lp_data->lp, head, soln);

   costs = (double *) malloc((vertnum*(vertnum-1)/2) * DSIZE);
   for (unbd_row_index = 0; unbd_row_index < lp_data->m; unbd_row_index++){
      if (soln[unbd_row_index] < -etol || (soln[unbd_row_index] > etol &&
					   head[unbd_row_index] < 0)){
	 mult = soln[unbd_row_index] < 0 ? 1 : -1;
	 CPXbinvarow(lp_data->cpxenv, lp_data->lp, unbd_row_index, z);
	 for (i = 0, equality = 0; i < lp_data->n; i++){
	    if (mult*z[i] < -etol) break;
	    if (fabs(z[i]) < etol) equality++;
	 }
	 if (i < lp_data->n) continue;

	 CPXbinvrow(lp_data->cpxenv, lp_data->lp, unbd_row_index, unbd_row);

	 if (fabs(unbd_row[lp_data->m - 1]) > etol){
	    beta = mult*unbd_row[lp_data->m-1];
	 }else{
	    beta = 0;
	 }

	 memset((char *)costs, 0, vertnum*(vertnum-1)/2 * DSIZE);

	 for (i = 0, v1 = 1; v1 < vertnum; v1++){
	    if (!(verts[v1].comp == comp_num)) continue;
	    for (v0 = 0; v0 < v1; v0++){
	       if (v0 && !(verts[v0].comp == comp_num)) continue;
	       index = INDEX(v0, v1);
	       if (i < num_arcs && arcs[i] == index){
		  if (indicators[sort_order[i]]){
		     costs[arcs[i]] = -100000;
		  }else{
		     if (fabs(unbd_row[sort_order[i]]) > etol)
			costs[arcs[i]] = mult*unbd_row[sort_order[i]];
		  }
		  i++;
	       }else{
		  costs[index] =
		     (double)((MAXINT)/(vrp->vertnum+vrp->numroutes-1));
	       }
	    }
	 }
	 for (alpha = beta, i = 0; i < num_arcs; i++){
	    if (indicators[i])
	       alpha += mult*unbd_row[i];
	 }

 	 memset(x, 0, (vertnum*(vertnum-1)/2)*ISIZE);

	 if (decomp_lower_bound(vrp, costs, x, 0, 1) < -alpha - etol){
	    matind = (int *)    malloc((vrp->vertnum+vrp->numroutes)*ISIZE);
	    matval = (double *) malloc((vrp->vertnum+vrp->numroutes)*DSIZE);
	    for (nzcnt = 0, i = 0; i < num_arcs; i++){
	       cur_edge = row_edges[i];
	       if ((coef = x[INDEX(cur_edge->v0, cur_edge->v1)]) > etol){
		  matind[nzcnt] = i;
		  matval[nzcnt++] = (double)coef;
	       }
	    }
	    matind[nzcnt] = lp_data->m-1;
	    matval[nzcnt++] = 1.0;
	    if (nzcnt > vrp->vertnum+vrp->numroutes){
	       printf("Too many nonzeros (%i) !!!!\n\n", nzcnt);
	       sleep(600);
	       exit();
	    }
	    matbeg[1] = nzcnt;
	    if (lp_data->n < lp_data->maxn){
	       add_cols(lp_data, 1, nzcnt, &obj, matbeg, matind, matval, &lb,
			&ub, 0);
	       lp_data->matbeg[lp_data->n] = lp_data->nz;
	    }
	    FREE(costs);
	    FREE(sort_order);
	    FREE(head);
	    FREE(arcs);
	    FREE(indicators);
	    FREE(unbd_row);
	    FREE(soln);
	    FREE(z);
	    FREE(x);
	    FREE(matval);
	    FREE(matind);
	    return(lp_data->n == lp_data->maxn ? -1 : 1);
	 }
      }
   }
   FREE(costs);
   FREE(sort_order);
   FREE(head);
   FREE(arcs);
   FREE(indicators);
   FREE(unbd_row);
   FREE(soln);
   FREE(z);
   FREE(x);
   return(0);
}

/*===========================================================================*/

#else

int vrp_generate_new_cols(cg_prob *p, LPdata *lp_data, network *n,
			  edge **row_edges, int comp_num)
{
   cg_vrp_spec *vrp = (cg_vrp_spec *)p->user;
   double *unbd_row;
   int unbd_row_index, mult; 
   int i, equality;
   int vertnum = vrp->vertnum; 
   int *head;
   double beta, *z, *soln;
   char *indicators;
   double etol = p->cur_sol.lpetol; 
   double *costs, lb = 0.0, ub = CPX_INFBOUND, *matval, obj = 0.0;
   int matbeg[2] = {0,0};
   int *matind, *x, nzcnt = 0, coef, cpx_status;

   if (!lp_data->n){
      costs = (double *) calloc(vertnum*(vertnum-1)/2, DSIZE);
      x = (int *) calloc(vertnum*(vertnum-1)/2, ISIZE);
      if (decomp_lower_bound(vrp, costs, x, 0, 1) == 0){
	 cpx_status = CPXsetintparam(lp_data->cpxenv, CPX_PARAM_SCAIND, -1);
	 cpx_status =
	    CPXsetintparam(lp_data->cpxenv, CPX_PARAM_BASINTERVAL, 2100000000);
	 cpx_status = CPXsetintparam(lp_data->cpxenv, CPX_PARAM_AGGIND, 0);
	 cpx_status = CPXsetintparam(lp_data->cpxenv, CPX_PARAM_DEPIND, 0);
	 cpx_status = CPXsetintparam(lp_data->cpxenv, CPX_PARAM_PREIND, 0);
	 
	 CPX_check_error("load_lp - CPXsetintparam");
	 
	 lp_data->lp =
	    CPXloadlp(lp_data->cpxenv,
		      (char *) "Decomp_prob", lp_data->n, lp_data->m, 1,
		      lp_data->obj,
		      lp_data->rhs, lp_data->sense, lp_data->matbeg,
		      lp_data->matcnt, lp_data->matind, lp_data->matval,
		      lp_data->lb, lp_data->ub, lp_data->rngval,
		      lp_data->maxn+lp_data->maxm, lp_data->maxm,
		      lp_data->maxnz+lp_data->maxm);

	 p->dcmp_data.iter_num = 0;
	 matind = (int *)    malloc((vrp->vertnum+vrp->numroutes)*ISIZE);
	 matval = (double *) malloc((vrp->vertnum+vrp->numroutes)*DSIZE);
	 for (nzcnt = 0, i = 0; i < lp_data->m - 1; i++){
	    if ((coef = x[i]) > etol){
	       matind[nzcnt] = i;
	       matval[nzcnt++] = (double)coef;
	    }
	 }
	 matind[nzcnt] = lp_data->m - 1;
	 matval[nzcnt++] = 1.0;
	 matbeg[1] = nzcnt;
	 if (lp_data->n < lp_data->maxn){
	    add_cols(lp_data, 1, nzcnt, &obj, matbeg, matind, matval, &lb,
		     &ub, 0);
	    lp_data->matbeg[lp_data->n] = lp_data->nz;
	 }
	 FREE(costs);
	 FREE(x);
	 FREE(matval);
	 FREE(matind);
	 return(lp_data->n == lp_data->maxn ? -1 : 1);
      }else{
	 return(0);
      }
   }
   
   x = (int *) calloc(vertnum*(vertnum-1)/2, ISIZE);
   z = (double *) calloc( MAX(lp_data->m, lp_data->n), DSIZE);
   soln = (double *) calloc(lp_data->m, DSIZE);
   head = (int *) calloc(lp_data->m, ISIZE);
   unbd_row = (double *) malloc(lp_data->m * DSIZE);
   
   CPXgetbhead(lp_data->cpxenv, lp_data->lp, head, soln);

   for (unbd_row_index = 0; unbd_row_index < lp_data->m; unbd_row_index++){
      if (soln[unbd_row_index] < -etol || (soln[unbd_row_index] > etol &&
					   head[unbd_row_index] < 0)){
	 mult = soln[unbd_row_index] < 0 ? 1 : -1;
	 cpx_status =
	    CPXbinvarow(lp_data->cpxenv, lp_data->lp, unbd_row_index, z);
	 for (i = 0, equality = 0; i < lp_data->n; i++){
	    if (mult*z[i] < -etol) break;
	    if (fabs(z[i]) < etol) equality++;
	 }
	 if (i < lp_data->n) continue;

	 cpx_status =
	    CPXbinvrow(lp_data->cpxenv, lp_data->lp, unbd_row_index, unbd_row);

	 if (fabs(unbd_row[lp_data->m - 1]) > etol){
	    beta = mult*unbd_row[lp_data->m-1];
	 }else{
	    beta = 0;
	 }

	 memset(x, 0, (vertnum*(vertnum-1)/2)*ISIZE);

	 for (i = 0; i < lp_data->m -1; i++)
	    unbd_row[i] *= mult;
	 
	 if (decomp_lower_bound(vrp, unbd_row, x, 0, mult) < -beta - etol){
	    matind = (int *)    malloc((vrp->vertnum+vrp->numroutes)*ISIZE);
	    matval = (double *) malloc((vrp->vertnum+vrp->numroutes)*DSIZE);
	    for (nzcnt = 0, i = 0; i < lp_data->m - 1; i++){
	       if ((coef = x[i]) > etol){
		  matind[nzcnt] = i;
		  matval[nzcnt++] = (double)coef;
	       }
	    }
	    matind[nzcnt] = lp_data->m-1;
	    matval[nzcnt++] = 1.0;
	    matbeg[1] = nzcnt;
	    if (lp_data->n < lp_data->maxn){
	       add_cols(lp_data, 1, nzcnt, &obj, matbeg, matind, matval, &lb,
			&ub, 0);
	       lp_data->matbeg[lp_data->n] = lp_data->nz;
	    }
	    FREE(head);
	    FREE(unbd_row);
	    FREE(soln);
	    FREE(z);
	    FREE(x);
	    FREE(matval);
	    FREE(matind);
	    return(lp_data->n == lp_data->maxn ? -1 : 1);
	 }
      }
   }
   FREE(head);
   FREE(unbd_row);
   FREE(soln);
   FREE(z);
   FREE(x);
   return(0);
}

#endif

/*===========================================================================*/

void delete_zero_rows(LPdata *lp_data, int bc_index, int iter_num)
{
   int *new_row_number = (int *) malloc(lp_data->m*ISIZE), new_row_num = 0;
   char *indicators = (char *) calloc(lp_data->m, ISIZE);
   FILE *f;
   int i, j, termcode, stat;
   char name1[50] = "";

   for (i = 0; i < lp_data->nz; i++)
      indicators[lp_data->matind[i]] = TRUE;
   
   for (i = 0; i < lp_data->m; i++){
      if (indicators[i]){
	 new_row_number[i] = new_row_num++;
      }else{
	 new_row_number[i] = -1;
      }
   }
   
   for (i = 0; i < lp_data->m; i++){
      if (indicators[i])
	 lp_data->sense[new_row_number[i]] = lp_data->sense[i];
   }
   
   for (i = 0; i < lp_data->nz; i++){
      lp_data->matind[i] = new_row_number[lp_data->matind[i]];
   }
   
   for (i = 0; i < lp_data->m; i++)
      if (indicators[i]){
	 lp_data->rhs[new_row_number[i]] = lp_data->rhs[i];
      }

   lp_data->m = new_row_num;
   
#if 0
   lp_data->lp =
      CPXloadlp(lp_data->cpxenv,
		(char *) "Decomp_prob", lp_data->n, lp_data->m, 1,
		lp_data->obj,
		lp_data->rhs, lp_data->sense, lp_data->matbeg, lp_data->matcnt,
		lp_data->matind, lp_data->matval, lp_data->lb, lp_data->ub,
		lp_data->rngval, lp_data->maxn+lp_data->maxm, lp_data->maxm,
		lp_data->maxnz+lp_data->maxm);


   termcode = CPXdualopt(lp_data->cpxenv, lp_data->lp);
   
   switch (stat = CPXgetstat(lp_data->cpxenv,lp_data->lp)){
    case CPX_OPTIMAL:              termcode = OPTIMAL; break;
    case CPX_INFEASIBLE:           termcode = D_INFEASIBLE; break;
    case CPX_UNBOUNDED:            termcode = D_UNBOUNDED; break;
    case CPX_OBJ_LIM:              termcode = D_OBJLIM; break;
    case CPX_IT_LIM_FEAS:
    case CPX_IT_LIM_INFEAS:        termcode = D_ITLIM; break;
    default:                       termcode = ABANDONED; break;
   }
#endif

#if 0   
   sprintf(name1,"/home/tkr/tmp/matrices/test.%i.%i.mps", bc_index, iter_num);
   
   f = fopen(name1, "w");
   
   fprintf(f, "NAME    %s\nROWS\n N      obj\n", name1);
   
   for (i = 0; i < lp_data->m; i++){
      if (indicators[i])
	 fprintf(f, " %c  %6ir\n", lp_data->sense[new_row_number[i]],
		 new_row_number[i]);
   }
   
   fprintf(f, "COLUMNS\n");
   
   for (j = 0; j < lp_data->n; j++){
      fprintf(f, " %6ix      obj  %f\n", j, lp_data->obj[j]);
      for (i = 0; i < lp_data->matcnt[j]; i++){
	 fprintf(f, " %6ix  %6ir  %f\n",
		 j, new_row_number[lp_data->matind[lp_data->matbeg[j]+i]],
		 lp_data->matval[lp_data->matbeg[j]+i]);
      }
   }
   
   fprintf(f, "RHS\n");
   
   for (i = 0; i < lp_data->m; i++)
      if (indicators[i]){
	 fprintf(f, "     rhs  %6ir  %f\n", new_row_number[i],
		 lp_data->rhs[new_row_number[i]]);
      }
	 
   fprintf(f, "BOUNDS\n");
   
   for (j = 0; j < lp_data->n; j++){
      fprintf(f, " LO  BOUND  %6ix      %f\n", j, lp_data->lb[j]);
      fprintf(f, " UP  BOUND  %6ix      %f\n", j, lp_data->ub[j]);
   }

   fprintf(f, "ENDATA\n");

   fclose(f);
#endif
}

/*===========================================================================*/

dcmp_col_set *user_generate_new_cols(cg_prob *p)
{
   return(NULL);
}

/*===========================================================================*/

void user_display_col(cg_prob *p, col_data *col)
{
}

/*===========================================================================*/

int user_check_col(cg_prob *p, int *colind, double *colval, int collen)
{
   return(0);
}

/*===========================================================================*/

void user_unpack_col(cg_prob *p, col_data *col, int *nzcnt, int *matind)
{
   memcpy ((char *) matind, col->coef, col->size);
}

/*===========================================================================*/

void user_pack_col(int *colind, int collen, col_data *col)
{
}

/*===========================================================================*/

void user_free_decomp_data_structures(cg_prob *p, void **user)
{
}

/*===========================================================================*/

char user_set_rhs(int varnum, double *rhs, int length, int *ind,
		  double *val, void *user)
{
   return(FALSE);
}
