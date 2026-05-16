import React from 'react'

export function ModuleMenu({ groups, activeId, onSelect }) {
  const handleSelectChange = (e) => {
    onSelect(e.target.value)
  }

  return (
    <>
      <div className="module-menu">
        {groups.map(group => (
          <div key={group.name} className="module-menu__group">
            <div className="module-menu__group-title">{group.name}</div>
            <div className="module-menu__items">
              {group.items.map(item => (
                <button
                  key={item.id}
                  className={item.id === activeId ? 'btn btn--active' : 'btn'}
                  onClick={() => onSelect(item.id)}
                  title={item.description}
                >
                  {item.title}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="module-select-wrap">
        <select className="module-select" value={activeId || ''} onChange={handleSelectChange}>
          {groups.map(group => (
            <optgroup key={group.name} label={group.name}>
              {group.items.map(item => (
                <option key={item.id} value={item.id}>{item.title}</option>
              ))}
            </optgroup>
          ))}
        </select>
      </div>
    </>
  )
}
