import React, { useEffect, useMemo, useState } from 'react'
import { getPetBaseAttrs, importTeam, setTeamMemberAttributes } from '../../lib/api'

const DEFAULT_TEXT = `### 阵容名
# 魔法：愿力强化
# 精灵名：冰系血脉、{技能1、技能2、技能3、技能4}`

const STAT_FIELDS = [
  { key: '生命', label: '生命' },
  { key: '物攻', label: '物攻' },
  { key: '魔攻', label: '魔攻' },
  { key: '物防', label: '物防' },
  { key: '魔防', label: '魔防' },
  { key: '速度', label: '速度' }
]

function createZeroStats() {
  return Object.fromEntries(STAT_FIELDS.map(field => [field.key, '0']))
}

function normalizeStats(stats) {
  const source = stats || {}
  return Object.fromEntries(STAT_FIELDS.map(field => [field.key, String(source[field.key] ?? 0)]))
}

function toCanonicalTeam(preview, sourceText) {
  return {
    name: preview.teamName,
    resonance_magic: preview.resonanceMagic,
    source_text: sourceText,
    members: (preview.members || []).map((member, index) => ({
      pet_name: member.pet_name || member.petName,
      bloodline: member.bloodline || '',
      skills: member.skills || [],
      stats: member.stats ? normalizeStats(member.stats) : null,
      member_index: member.member_index ?? index
    }))
  }
}

async function enrichMembersWithBaseStats(members) {
  const items = await Promise.all(
    (members || []).map(async member => {
      const petName = member.pet_name || member.petName
      if (!petName) {
        return {
          ...member,
          stats: null
        }
      }

      try {
        const payload = await getPetBaseAttrs(petName)
        return {
          ...member,
          stats: payload?.base_attrs || null
        }
      } catch (error) {
        return {
          ...member,
          stats: null
        }
      }
    })
  )

  return items
}

function parseTeamPreview(text) {
  const lines = String(text || '')
    .split(/\r?\n/)
    .map(line => line.trim())
    .filter(Boolean)

  const teamLine = lines.find(line => line.startsWith('###')) || ''
  const magicLine = lines.find(line => /^#\s*魔法[:：]/.test(line)) || ''
  const members = lines
    .filter(line => /^#\s*[^#：]+\s*：/.test(line) && !/^#\s*魔法[:：]/.test(line))
    .map(line => {
      const match = line.match(/^#\s*([^：#]+?)\s*：\s*([^、]+?)\s*、\s*\{([^}]*)\}\s*$/)
      if (!match) return null
      return {
        petName: match[1].trim(),
        bloodline: match[2].trim(),
        skills: match[3].split('、').map(item => item.trim()).filter(Boolean)
      }
    })
    .filter(Boolean)

  return {
    teamName: teamLine.replace(/^###\s*/, '').trim(),
    resonanceMagic: magicLine.replace(/^#\s*魔法[:：]\s*/, '').trim(),
    members
  }
}

export function TeamImportModule() {
  const [text, setText] = useState(DEFAULT_TEXT)
  const [teamData, setTeamData] = useState(null)
  const [isPersisted, setIsPersisted] = useState(false)
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')
  const [loading, setLoading] = useState(false)
  const [teamName, setTeamName] = useState('')
  const [petName, setPetName] = useState('')
  const [stats, setStats] = useState(createZeroStats())

  const preview = useMemo(() => parseTeamPreview(text), [text])
  const members = teamData?.members || []
  const currentTeamName = teamName || teamData?.name || preview.teamName
  const currentPetName = petName || members[0]?.pet_name || members[0]?.petName || ''
  const currentMember = useMemo(() => {
    return members.find(member => (member.pet_name || member.petName) === currentPetName) || null
  }, [currentPetName, members])

  const currentMemberStats = useMemo(() => {
    return normalizeStats(currentMember?.stats)
  }, [currentMember])

  useEffect(() => {
    setStats(currentMember?.stats ? normalizeStats(currentMember.stats) : createZeroStats())
  }, [currentTeamName, currentPetName, currentMember])

  const updateStat = (key, value) => {
    setStats(current => ({ ...current, [key]: value }))
  }

  const handleStageImport = async () => {
    setError('')
    setInfo('')

    if (!preview.teamName) {
      setError('未识别到队伍名，请检查首行 ### 队伍名')
      return
    }
    if (!preview.resonanceMagic) {
      setError('未识别到共鸣魔法，请检查 # 魔法：...')
      return
    }
    if (!preview.members.length) {
      setError('未识别到精灵列表，请检查每行格式')
      return
    }

    setLoading(true)
    try {
      const stagedTeam = toCanonicalTeam(preview, text)
      const enrichedMembers = await enrichMembersWithBaseStats(stagedTeam.members)
      const enrichedTeam = {
        ...stagedTeam,
        members: enrichedMembers
      }
      setTeamData(enrichedTeam)
      setIsPersisted(false)
      setTeamName(enrichedTeam.name)
      setPetName(enrichedTeam.members[0]?.pet_name || '')
      setStats(normalizeStats(enrichedTeam.members[0]?.stats))
      setInfo('已解析到本地缓存，基础属性已自动回填。点击“确认写入数据库”后才会入库。')
    } catch (err) {
      setError(err.message || '解析失败')
    } finally {
      setLoading(false)
    }
  }

  const handleConfirmImport = async () => {
    setLoading(true)
    setError('')
    setInfo('')
    try {
      const payload = await importTeam(text)
      const persistedTeam = payload?.team || null
      setTeamData(persistedTeam)
      setIsPersisted(true)
      setTeamName(persistedTeam?.name || preview.teamName || '')
      setPetName(persistedTeam?.members?.[0]?.pet_name || persistedTeam?.members?.[0]?.petName || '')
      setStats(normalizeStats(persistedTeam?.members?.[0]?.stats))
      setInfo(`已写入数据库：${persistedTeam?.name || ''}`)
    } catch (err) {
      setError(err.message || '写入数据库失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSaveAttributes = async () => {
    if (!currentTeamName || !currentPetName) {
      setError('请先选择队伍和精灵')
      return
    }

    const payload = Object.fromEntries(
      STAT_FIELDS.map(field => [field.key, Number(stats[field.key])])
    )

    if (Object.values(payload).some(Number.isNaN)) {
      setError('六维属性必须都是数字')
      return
    }

    setLoading(true)
    setError('')
    setInfo('')
    try {
      const nextStats = normalizeStats(payload)

      if (!isPersisted) {
        setTeamData(current => {
          if (!current) return current
          return {
            ...current,
            members: (current.members || []).map(member => {
              const name = member.pet_name || member.petName
              if (name !== currentPetName) {
                return member
              }
              return {
                ...member,
                stats: nextStats
              }
            })
          }
        })
        setStats(nextStats)
        setInfo('当前为本地缓存模式，属性仅保存在前端。确认写入数据库后才会持久化。')
        return
      }

      await setTeamMemberAttributes(currentTeamName, currentPetName, payload)
      setStats(nextStats)
      setTeamData(current => ({
        ...(current || {}),
        members: (current?.members || []).map(member => {
          const name = member.pet_name || member.petName
          if (name !== currentPetName) {
            return member
          }

          return {
            ...member,
            stats: nextStats
          }
          })
      }))
      setInfo(`已更新数据库中 ${currentPetName} 的六维属性。`)
    } catch (err) {
      setError(err.message || '保存属性失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="module-card module-team-page module-team-page--compact">
      <div className="module-kicker">队伍导入</div>
      <div className="module-page-header module-page-header--stacked">
        <div>
          <h2>导入队伍并补录属性</h2>
          <p>先解析到前端缓存，再点确定写入数据库。未确定前不会入库。</p>
        </div>
        <div className="module-chip-list">
          <span className="module-chip">POST /teams/import</span>
          <span className="module-chip">POST /teams/.../attributes</span>
        </div>
      </div>

      <div className="module-stack">
        <section className="module-panel module-panel--boxed">
          <div className="panel-title">1. 阵容文本</div>
          <div className="sub-box">
            <textarea
              className="team-textarea team-textarea--compact"
              value={text}
              onChange={event => setText(event.target.value)}
              spellCheck={false}
            />
          </div>
          <div className="sub-box sub-box--actions">
            <div className="module-actions module-actions--tight">
              <button className="btn" onClick={handleStageImport} disabled={loading}>
                解析到本地缓存
              </button>
              <button className="btn btn--primary" onClick={handleConfirmImport} disabled={loading}>
                {loading ? '处理中...' : '确认写入数据库'}
              </button>
              <button className="btn" onClick={() => setText(DEFAULT_TEXT)} disabled={loading}>
                填充模板
              </button>
              <button
                className="btn"
                onClick={() => {
                  setText('')
                  setTeamData(null)
                  setIsPersisted(false)
                  setTeamName('')
                  setPetName('')
                  setStats(createZeroStats())
                  setError('')
                  setInfo('')
                }}
                disabled={loading}
              >
                清空
              </button>
            </div>
            {error ? <div className="notice notice--error">{error}</div> : null}
            {info ? <div className="notice notice--success">{info}</div> : null}
            <details className="import-help">
              <summary>格式说明</summary>
              <div>第一行写队伍名，第二行写共鸣魔法，后面每行写一个精灵的血脉和 4 个技能。</div>
            </details>
          </div>
        </section>

        <section className="module-panel module-panel--boxed">
          <div className="panel-title">2. 选择队伍与精灵</div>
          <div className="sub-box sub-box--form">
            <div className="field-stack">
              <label className="field-label">队伍名</label>
              <input className="team-input" value={teamName} onChange={event => setTeamName(event.target.value)} placeholder="导入后自动填充" />
            </div>
            <div className="field-stack">
              <label className="field-label">精灵名</label>
              <select className="team-input" value={petName} onChange={event => setPetName(event.target.value)}>
                <option value="">请选择精灵</option>
                {members.map(member => {
                  const value = member.pet_name || member.petName
                  return <option key={value} value={value}>{value}</option>
                })}
              </select>
            </div>
          </div>
          <div className="sub-box preview-strip">
            <div className="preview-chip">
              <span>共鸣魔法</span>
              <strong>{teamData?.resonance_magic || preview.resonanceMagic || '未识别'}</strong>
            </div>
            <div className="preview-chip">
              <span>成员数</span>
              <strong>{members.length}</strong>
            </div>
            <div className="preview-chip">
              <span>当前状态</span>
              <strong>{isPersisted ? '已写入数据库' : '仅前端缓存'}</strong>
            </div>
          </div>
          <div className="sub-box">
            <div className="field-stack">
              <div className="field-label">当前宠物属性预览</div>
              <div className="member-name">{currentPetName || '未选择'}</div>
            </div>
            <div className="stats-line stats-line--compact">
              {STAT_FIELDS.map(field => (
                <span key={field.key} className="stat-pill">
                  {field.label} {currentMemberStats[field.key]}
                </span>
              ))}
            </div>
          </div>
        </section>

        <section className="module-panel module-panel--boxed">
          <div className="panel-title">3. 六维属性</div>
          <div className="sub-box">
            <div className="stats-grid stats-grid--compact">
              {STAT_FIELDS.map(field => (
                <label key={field.key} className="stat-field">
                  <span>{field.label}</span>
                  <input
                    className="team-input team-input--small"
                    inputMode="numeric"
                    value={stats[field.key]}
                    onChange={event => updateStat(field.key, event.target.value)}
                    placeholder="0"
                  />
                </label>
              ))}
            </div>
          </div>
          <div className="sub-box sub-box--actions">
            <button className="btn btn--primary" onClick={handleSaveAttributes} disabled={loading}>
              保存六维属性
            </button>
          </div>
        </section>

        <section className="module-panel module-panel--boxed">
          <div className="panel-title">4. 成员概览</div>
          <div className="sub-box">
            {members.length ? (
              <div className="member-summary-list">
                {members.map(member => {
                  const name = member.pet_name || member.petName
                  const memberStats = normalizeStats(member.stats)
                  return (
                    <div key={name} className="member-summary-card">
                      <div className="member-summary-card__head">
                        <div>
                          <div className="member-name">{name}</div>
                          <div className="member-meta">{member.bloodline || '未知血脉'}</div>
                        </div>
                        <div className="badge">{(member.skills || []).length} 技能</div>
                      </div>
                      <div className="skill-tags">
                        {(member.skills || []).map(skill => <span key={skill} className="skill-tag">{skill}</span>)}
                      </div>
                      <div className="stats-line stats-line--compact">
                        {STAT_FIELDS.map(field => (
                          <span key={field.key} className="stat-pill">
                            {field.label} {memberStats[field.key]}
                          </span>
                        ))}
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="empty-state">暂无成员预览。</div>
            )}
          </div>
        </section>
      </div>
    </section>
  )
}
