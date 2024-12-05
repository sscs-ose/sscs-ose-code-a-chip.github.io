BEGIN{
   i = 0;
   p = -1;
   max_num_procs = -1
}

($1 == "Procs"){
   p++;
   i = 0;
   if (max_num_procs < 0){
      max_num_procs = $2
   }
   num_procs[p] = $2
}

($7 == "ok"){
   if ($6 < 3600){
      if (num_procs[p] == max_num_procs){
	 name[i] = $1;
      }
      time[i, p] = $6;
   }else{
      name[i] = "unsolved";
      time[i, p] = 10000;
   }
   nodes[i, p] = $5;
   i++;
}

($7 == "stopped"){
   if (num_procs[p] == max_num_procs){
      name[i] = "unsolved";
   }
   time[i, p] = 100000;
   nodes[i, p] = $5;
   i++;
}

($7 == "abort"){
   if (num_procs[p] == max_num_procs){
      name[i] = "unsolved";
   }
   time[i, p] = 10000;
   nodes[i, p] = 10000;
   i++;
}

END{
   for (l = 0; l <= p; l++){
      filename = sprintf("pprof_%s.out", num_procs[l]);
      for (k = 0; k < i; k++){
	 if (name[k] != "unsolved"){
	    printf("%30s %11.3f %11d\n", name[k], time[k,l], nodes[k,l]) > filename;
	 }
      }
   }
}
