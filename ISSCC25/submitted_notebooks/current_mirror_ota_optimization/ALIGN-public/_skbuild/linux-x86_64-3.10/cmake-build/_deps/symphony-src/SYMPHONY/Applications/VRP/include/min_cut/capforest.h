#ifndef _CAPFOREST_H
#define _CAPFOREST_H

#include "sym_proto.h"
#include "network.h"

float capforest PROTO((network *n, int Vertnum, char scannedmark));
float increment PROTO((vertex *v, float inc, vertex **tnodes, int *lnt));
/* If the v is in the tree, then increases its value with inc,
   otherwise inserts v into the tree with value inc.
   Returns the incremented value of v.*/
vertex *delmax PROTO((vertex **treenodes, int *lnt));
/* Erases and returns the maximum element in the tree. */

#endif
