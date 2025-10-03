const fs = require('fs');
const path = require('path');

const filePath = path.join(__dirname, 'app', 'static', 'md3', 'components', 'floorplan-planner.js');
let content = fs.readFileSync(filePath, 'utf8');

const replacements = [
  {
    search: `    state.canvasEl.addEventListener('pointerleave', (event) => {\n      if (state.isSettingScale) {`,
    replace: `    state.canvasEl.addEventListener('pointerleave', (event) => {\n      if (state.isSettingScale) {`
  },
];

for (const { search, replace } of replacements) {
  if (!content.includes(search)) {
    console.error('Pattern not found:', search);
    process.exit(1);
  }
  content = content.replace(search, replace);
}

fs.writeFileSync(filePath, content, 'utf8');
console.log('Patch applied.');
