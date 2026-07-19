import { NavLink } from 'react-router-dom';

/**
 * Элемент навигации для отдельной кампании с древовидной структурой (Tree-lines).
 * 
 * Стилизация (по запросу пользователя):
 * - Активный пункт: сочный фирменный индиго фон #5E44EB (chatico-indigo), белый текст (text-white)
 *   для идеального контраста, плюс яркий лаймовый маркер (bg-[#c2f913]) у левого края.
 * - Покой: прозрачный фон, серый текст (text-gray-500)
 * - Hover: мягкая светло-серая подложка (hover:bg-gray-50)
 */
export default function CampaignNavItem({ id, name, status, isLast }) {
  const isPaused = status === 'paused';

  return (
    <NavLink
      to={`/campaigns/${id}`}
      title={name}
      className={({ isActive }) =>
        [
          'group relative flex w-full min-w-0 items-center justify-between rounded-lg py-2 pl-3 pr-3 text-sm font-medium transition-all duration-150',
          isActive
            ? 'bg-[#5E44EB] text-white font-bold shadow-sm'
            : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900',
        ].join(' ')
      }
    >
      {({ isActive }) => (
        <>
          {/* Вертикальная линия-направляющая дерева */}
          <div
            className="absolute -left-3 top-0 w-px bg-gray-200"
            style={{ height: isLast ? '50%' : '100%' }}
          />

          {/* Горизонтальное ответвление дерева */}
          <div className="absolute -left-3 top-1/2 h-px w-3 bg-gray-200" />

          {/* Яркий лаймовый маркер у левого края активного пункта */}
          {isActive && (
            <div className="absolute left-0 top-2 bottom-2 w-[4px] rounded-r-md bg-[#c2f913]" />
          )}

          {/* Название кампании */}
          <span className="min-w-0 flex-1 truncate pr-2">
            {name}
          </span>

          {/* Компактный бейдж статуса */}
          {isPaused && (
            <span
              className={[
                'shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-semibold tracking-wide transition-colors',
                isActive
                  ? 'bg-white/20 text-white'
                  : 'bg-gray-100 text-gray-500 group-hover:bg-gray-200',
              ].join(' ')}
              aria-label="На паузе"
            >
              пауза
            </span>
          )}
        </>
      )}
    </NavLink>
  );
}
