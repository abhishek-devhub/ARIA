export function generateMarkdownReport(state) {
  const { question, summary, contradictions, gaps, papers } = state;
  
  let md = `# Research Report: ${question}\n\n`;
  
  if (summary) {
    md += `${summary}\n\n`;
  }
  
  if (contradictions) {
    md += `---\n\n`;
    md += `${contradictions}\n\n`;
  }
  
  if (gaps && gaps.gaps && gaps.gaps.length > 0) {
    md += `---\n\n## Research Gaps\n\n`;
    gaps.gaps.forEach(g => {
      md += `### ${g.rank}. ${g.gap}\n`;
      md += `**Evidence:** ${g.evidence}\n\n`;
      md += `**Importance:** ${g.importance}\n\n`;
    });
  }
  
  if (papers && papers.length > 0) {
    md += `---\n\n## References\n\n`;
    papers.forEach((p, i) => {
      md += `${i + 1}. **${p.title}** (${p.year || 'n.d.'}). `;
      if (p.authors && p.authors.length > 0) {
        md += `*${p.authors.slice(0, 3).join(', ')}${p.authors.length > 3 ? ' et al.' : ''}*. `;
      }
      if (p.url) {
        md += `[Link](${p.url})\n`;
      } else {
        md += `\n`;
      }
    });
  }
  
  return md;
}

export function downloadMarkdown(state) {
  if (!state || !state.question) return;

  const md = generateMarkdownReport(state);
  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  
  const a = document.createElement('a');
  a.href = url;
  
  // Create a clean filename
  const cleanFilename = state.question
    .substring(0, 40)
    .replace(/[^a-z0-9]/gi, '_')
    .toLowerCase();
    
  a.download = `ARIA_Report_${cleanFilename || 'untitled'}.md`;
  
  // Trigger download
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
