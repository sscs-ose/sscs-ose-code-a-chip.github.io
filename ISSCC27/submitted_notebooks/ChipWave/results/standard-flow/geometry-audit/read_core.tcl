read_db /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-5618245a667f4befa40aaf23b428464d/build/pnr/results/6_final.odb
set block [ord::get_db_block]
set core [$block getCoreArea]
set die [$block getDieArea]
puts "CORE_AUDIT dbu=[$block getDbUnitsPerMicron] core=[$core xMin],[$core yMin],[$core xMax],[$core yMax] die=[$die xMin],[$die yMin],[$die xMax],[$die yMax]"
