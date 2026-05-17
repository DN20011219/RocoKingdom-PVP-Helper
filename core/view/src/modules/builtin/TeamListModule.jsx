import React, { useEffect, useMemo, useState } from 'react'
import { getTeam, getTeams, setTeamMemberAttributes } from '../../lib/api'

const STAT_FIELDS = [
  { key: '生命', label: '生命' },
  { key: '物攻', label: '物攻' },
  { key: '魔攻', label: '魔攻' },
  { key: '物防', label: '物防' },
  { key: '魔防', label: '魔防' },
  { key: '速度', label: '速度' }
]

function normalizeStats(stats) {
  const source = stats || {}
  return Object.fromEntries(STAT_FIELDS.map(field => [field.key, source[field.key] ?? 0]))
}

function normalizeStatsInput(stats) {
  const source = stats || {}
  return Object.fromEntries(STAT_FIELDS.map(field => [field.key, String(source[field.key] ?? 0)]))
}

function createZeroStatsInput() {
  return Object.fromEntries(STAT_FIELDS.map(field => [field.key, '0']))
}

function formatMember(member) {
  return {
    name: member.pet_name || member.petName,
    bloodline: member.bloodline,
    skills: member.skills || [],
    stats: member.stats || null
  }
}

export function TeamListModule() {
  const [teams, setTeams] = useState([])
  const [selectedName, setSelectedName] = useState('')
  const [selectedTeam, setSelectedTeam] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [selectedPetName, setSelectedPetName] = useState('')
  const [editingStats, setEditingStats] = useState(createZeroStatsInput())
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState('')
  const [saveInfo, setSaveInfo] = useState('')

  const loadTeams = async (silent = false) => {
    if (silent) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }

    try {
      const payload = await getTeams()
      const list = payload?.teams || []
      setTeams(list)
      if (!selectedName && list.length) {
        setSelectedName(list[0].name)
      }
      if (!list.length) {
        setSelectedTeam(null)
      }
    } catch (err) {
      setTeams([])
      setSelectedTeam(null)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    loadTeams()
  }, [])

  useEffect(() => {
    if (!selectedName) {
      setSelectedTeam(null)
      return
    }

    let cancelled = false

    const loadDetail = async () => {
      try {
        const payload = await getTeam(selectedName)
        if (!cancelled) {
          setSelectedTeam(payload)
        }
      } catch (err) {
        if (!cancelled) {
          setSelectedTeam(null)
        }
      }
    }

    loadDetail()

    return () => {
      cancelled = true
    }
  }, [selectedName])

  const detailMembers = useMemo(
    () => (selectedTeam?.members || []).map(formatMember),
    [selectedTeam]
  )

  useEffect(() => {
    if (!detailMembers.length) {
      setSelectedPetName('')
      setEditingStats(createZeroStatsInput())
      return
    }

    setSelectedPetName(current => {
      if (current && detailMembers.some(member => member.name === current)) {
        return current
      }
      return detailMembers[0].name
    })
  }, [detailMembers])

  useEffect(() => {
    const member = detailMembers.find(item => item.name === selectedPetName)
    setEditingStats(member?.stats ? normalizeStatsInput(member.stats) : createZeroStatsInput())
  }, [detailMembers, selectedPetName])

  const updateEditingStat = (key, value) => {
    setEditingStats(current => ({ ...current, [key]: value }))
  }

  const handleSaveMemberStats = async () => {
    if (!selectedTeam?.name || !selectedPetName) {
      setSaveError('请先选择队伍和宠物')
      return
    }

    const payload = Object.fromEntries(STAT_FIELDS.map(field => [field.key, Number(editingStats[field.key])]))
    if (Object.values(payload).some(Number.isNaN)) {
      setSaveError('六维属性必须为数字')
      return
    }

    setSaving(true)
    setSaveError('')
    setSaveInfo('')
    try {
      await setTeamMemberAttributes(selectedTeam.name, selectedPetName, payload)
      setSelectedTeam(current => {
        if (!current) return current
        return {
          ...current,
          members: (current.members || []).map(member => {
            const name = member.pet_name || member.petName
            if (name !== selectedPetName) {
              return member
            }
            return {
              ...member,
              stats: payload
            }
          })
        }
      })
      setSaveInfo(`已更新 ${selectedPetName} 的六维属性。`)
    } catch (err) {
      setSaveError(err.message || '更新失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="module-card module-team-page module-team-page--compact">
      <div className="module-kicker">队伍列表</div>
      <div className="module-page-header module-page-header--stacked">
        <div>
          <h2>已导入队伍</h2>
          <p>点击左侧队伍可查看右侧详情。网络失败时仅显示空状态，不显示额外错误块。</p>
        </div>
        <div className="module-chip-list">
          <span className="module-chip">GET /teams</span>
          <span className="module-chip">GET /teams/{'{team_name}'}</span>
        </div>
      </div>

      <div className="module-stack">
        <section className="module-panel">
          <div className="panel-title-row">
            <div className="panel-title">队伍列表</div>
            <button className="btn" onClick={() => loadTeams(true)} disabled={refreshing || loading}>
              {refreshing ? '刷新中...' : '刷新'}
            </button>
          </div>

          {loading ? (
            <div className="empty-state">正在加载队伍...</div>
          ) : teams.length ? (
            <div className="team-list team-list--compact">
              {teams.map(team => (
                <button
                  key={team.name}
                  className={team.name === selectedName ? 'team-card team-card--active' : 'team-card'}
                  onClick={() => setSelectedName(team.name)}
                >
                  <div className="team-card__name">{team.name}</div>
                  <div className="team-card__meta">{team.resonance_magic || '未设置共鸣魔法'}</div>
                </button>
              ))}
            </div>
          ) : (
            <div className="empty-state">当前还没有导入任何队伍。</div>
          )}
        </section>

        <section className="module-panel">
          <div className="panel-title">详细数据</div>
          {!selectedTeam ? (
            <div className="empty-state">请选择左侧队伍。</div>
          ) : (
            <>
              <div className="detail-hero detail-hero--compact">
                <div className="detail-hero__name">{selectedTeam.name}</div>
                <div className="detail-hero__meta">{selectedTeam.resonance_magic || '未设置共鸣魔法'}</div>
              </div>

              <div className="detail-summary detail-summary--compact">
                <div className="mini-card">
                  <div className="mini-card__label">成员数量</div>
                  <div className="mini-card__value">{detailMembers.length}</div>
                </div>
                <div className="mini-card">
                  <div className="mini-card__label">原始导入</div>
                  <div className="mini-card__value">{selectedTeam.source_text ? '已保存' : '无'}</div>
                </div>
              </div>

              <div className="sub-box sub-box--form">
                <div className="panel-title">属性编辑</div>
                <div className="field-stack">
                  <label className="field-label">选择宠物</label>
                  <select className="team-input" value={selectedPetName} onChange={event => setSelectedPetName(event.target.value)}>
                    <option value="">请选择宠物</option>
                    {detailMembers.map(member => (
                      <option key={member.name} value={member.name}>{member.name}</option>
                    ))}
                  </select>
                </div>

                <div className="stats-grid stats-grid--compact">
                  {STAT_FIELDS.map(field => (
                    <label key={field.key} className="stat-field">
                      <span>{field.label}</span>
                      <input
                        className="team-input team-input--small"
                        inputMode="numeric"
                        value={editingStats[field.key]}
                        onChange={event => updateEditingStat(field.key, event.target.value)}
                        placeholder="0"
                      />
                    </label>
                  ))}
                </div>

                <div className="module-actions module-actions--tight">
                  <button className="btn btn--primary" onClick={handleSaveMemberStats} disabled={saving || !selectedPetName}>
                    {saving ? '保存中...' : '保存到数据库'}
                  </button>
                </div>
                {saveError ? <div className="notice notice--error">{saveError}</div> : null}
                {saveInfo ? <div className="notice notice--success">{saveInfo}</div> : null}
              </div>

              <div className="detail-member-list detail-member-list--compact">
                {detailMembers.map(member => (
                  <div key={member.name} className="detail-member-card">
                    <div className="detail-member-card__top">
                      <div>
                        <div className="detail-member-card__name">{member.name}</div>
                        <div className="detail-member-card__bloodline">{member.bloodline || '未知血脉'}</div>
                      </div>
                      {member.stats ? <div className="badge badge--success">已补录属性</div> : <div className="badge">未补录属性</div>}
                    </div>

                    <div className="skill-tags">
                      {member.skills.length ? member.skills.map(skill => <span key={skill} className="skill-tag">{skill}</span>) : <span className="skill-tag skill-tag--empty">无技能</span>}
                    </div>

                    <div className="stats-line stats-line--compact">
                      {member.stats ? (() => {
                        const stats = normalizeStats(member.stats)
                        return STAT_FIELDS.map(field => (
                          <span key={field.key} className="stat-pill">
                            {field.label} {stats[field.key]}
                          </span>
                        ))
                      })() : <span className="stats-empty">暂无六维属性</span>}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </section>
      </div>
    </section>
  )
}
