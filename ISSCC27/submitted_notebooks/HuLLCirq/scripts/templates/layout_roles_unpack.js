// Installed string-table-v1 decoder. Never load executable archive content.
const unpackLayoutData = data => {
  if (data.cell_encoding !== 'string-table-v1') return data;
  const strings = data.strings;
  data.cells = data.cell_rows.map(row => ({
    id: strings[row[0]], master: strings[row[1]], bbox: row[2],
    role: strings[row[3]], status: strings[row[4]],
    evidence: row[5].map(index => strings[index]),
  }));
  delete data.strings;
  delete data.cell_rows;
  return data;
};
