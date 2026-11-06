const fs = require('node:fs');
const path = require('node:path');
// @dbml/core is an optional design-time dependency, never needed by the API.
const {Parser, ModelExporter} = require(process.env.DBML_CORE_PATH || '@dbml/core');
const model = new Parser().parse(fs.readFileSync(path.resolve(__dirname, '../../content-atelier-compact.dbml'),'utf8'), 'dbmlv2');
const sql = '-- Approved thirteen-table baseline. Run only through storage_cli init.\nCREATE EXTENSION IF NOT EXISTS vector;\n' + ModelExporter.export(model, 'postgres') + '\nCREATE INDEX angle_moments_reverse ON angle_moments(moment_id);\n';
fs.writeFileSync(path.join(__dirname, '001_approved_schema.sql'),sql);
