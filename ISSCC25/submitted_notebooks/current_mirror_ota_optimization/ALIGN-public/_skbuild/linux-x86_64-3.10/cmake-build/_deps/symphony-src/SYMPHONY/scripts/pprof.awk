BEGIN{
   i = 0;
}

($7 == "ok"){
   name[i] = $1;
   time[i] = $6;
   nodes[i] = $5;
   i++;
}

($7 == "stopped"){
   name[i] = $1;
   time[i] = 100000;
   nodes[i] = $5;
   i++;
}

($7 == "abort"){
   name[i] = "abort";
   time[i] = 10000;
   nodes[i] = 10000;
   i++;
}

END{
   for (k = 0; k < i; k++){
      printf("%30s %11.3f %11d\n", name[k], time[k], nodes[k]);
   }
}
