/**
 * SkillInfoBanner — at-a-glance Skill match indicator at the top of assistant messages.
 *
 * Mutually exclusive with skill-need-more-info and skill-failure banners
 * (priority: failure > need_more_info > info).
 */
export default function SkillInfoBanner({ skill_name, category, tools = [], onClick }) {
  const visibleTools = tools.slice(0, 3);
  const remaining = tools.length - 3;

  return (
    <div className="skill-info-banner" onClick={onClick}>
      <span className="skill-info-icon">🎯</span>
      <span className="skill-info-text">已匹配 Skill: {skill_name}</span>
      <span className="skill-category-badge">
        {category === 'preset' ? '预设' : category === 'custom' ? '自定义' : category}
      </span>
      {visibleTools.map(t => (
        <span key={t} className="skill-tool-chip">🔧 {t}</span>
      ))}
      {remaining > 0 && (
        <span className="skill-tool-chip-more">+{remaining} more</span>
      )}
    </div>
  );
}
