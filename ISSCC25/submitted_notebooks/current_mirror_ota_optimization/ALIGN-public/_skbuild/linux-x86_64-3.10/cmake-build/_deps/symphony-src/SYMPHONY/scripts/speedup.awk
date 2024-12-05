BEGIN{
   p = -1;
}

($1 == "Procs"){
   p++;
   i = 0;
   num_procs[p] = $2
   printf("Now starting to read file with procs %i \n", num_procs[p]);
}

($7 == "ok"){
   if (num_procs[p] == 1){
      name[i] = $1;
      time[i] = $6;
      nodes[i] = $5;
   }else{
      if (time[i] < 0.1){
	 speedup[i,num_procs[p]] = -5;
      }else{
	 if ($6 != 0){
	    speedup[i,num_procs[p]] = time[i]/$6;
	 }else{
	    speedup[i,num_procs[p]] = 10000;
	 }
      } 
      if ($5 != 0){
	 node_ratio[i,num_procs[p]] = nodes[i]/$5;
      }else{
	 node_ratio[i,num_procs[p]] = -10;
      }
   }
   i++;
}

($7 == "stopped"){
   if (num_procs[p] == 1){
      name[i] = $1;
      time[i] = -$4;
      nodes[i] = $5;
   }else{
      if (time[i] < 0.1){
	 if (time[i] <= -0.1 && $4 >= 0.1){
	    speedup[i,num_procs[p]] = time[i]/$4;
	 }else{
	    speedup[i,num_procs[p]] = -100000;
	 }
      }else{
	 speedup[i,num_procs[p]] = -1;
      }	 
   }
   i++;
}

($7 == "abort"){
   if (num_procs[p] == 1){
      name[i] = "abort";
   }
   i++;
}

END{
   for (k = 0; k < i; k++){
      if (name[k] != "abort"){
	 printf("%10s ", name[k]);
	 for (j = 0; j <= p; j++){
	    printf("%11.3f ", speedup[k, num_procs[j]]);
	 } 
	 printf("\n");
      }
   }
}
