import { Link } from 'react-router-dom';

const LOGO_SRC = '/logo-chatico-ads.png';

/**
 * Логотип Chatico ADS на основе оригинального файла /logo-chatico-ads.png.
 * Применяет SVG-фильтр #chroma-key-black для удаления черного фона в браузере,
 * делая его абсолютно прозрачным без потери качества оригинальных цветов.
 */
export default function Logo({ className = '', height = 28, to }) {
  const image = (
    <img
      src={LOGO_SRC}
      alt="chatico ads"
      className={`block object-contain object-left ${className}`}
      height={height}
      style={{ 
        height, 
        width: 'auto',
        filter: 'url(#chroma-key-black)', // Применяем хромакей черного цвета
      }}
      draggable={false}
    />
  );

  if (to) {
    return (
      <Link to={to} className="inline-flex shrink-0" aria-label="Chatico ADS — на главную">
        {image}
      </Link>
    );
  }

  return image;
}

export { LOGO_SRC };
