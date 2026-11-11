import confirmationSfxUrl from "@/assets/sound/confirmation_sfx.mp3";
import notificationSfxUrl from "@/assets/sound/notification_sfx.mp3";
import alertSfxUrl from "@/assets/sound/alert_sfx.mp3";
import cautionSfxUrl from "@/assets/sound/caution_sfx.mp3";

const audios = {
  confirmacao: { url: confirmationSfxUrl, instance: null, ultimo: 0 },
  notificacao: { url: notificationSfxUrl, instance: null, ultimo: 0 },
  alerta: { url: alertSfxUrl, instance: null, ultimo: 0 },
  atencao: { url: cautionSfxUrl, instance: null, ultimo: 0 },
};

function reproduzir(chave, throttleMs = 500) {
  const item = audios[chave];
  if (!item) return;

  const agora = Date.now();
  if (agora - item.ultimo < throttleMs) {
    return;
  }
  item.ultimo = agora;

  try {
    if (!item.instance) {
      item.instance = new Audio(item.url);
    } else {
      item.instance.currentTime = 0;
    }
    item.instance.volume = 0.6;
    const playPromise = item.instance.play();
    if (playPromise !== undefined) {
      playPromise.catch((err) => {
        console.debug(`Autoplay do som [${chave}] aguardando interação:`, err);
      });
    }
  } catch (erro) {
    console.debug(`Erro ao tocar som [${chave}]:`, erro);
  }
}

/**
 * Toca quando cadastrar, importar, salvar ou finalizar uma etapa com sucesso (confirmation_sfx.mp3).
 */
export function tocarSomConfirmacao() {
  reproduzir("confirmacao", 600);
}

/**
 * Toca quando receber notificações do sistema / agenda / prazos (notification_sfx.mp3).
 * Throttle de 1.2s para evitar repetição em lote.
 */
export function tocarSomNotificacao() {
  reproduzir("notificacao", 1200);
}

/**
 * Toca em caso de erro, falha ou ação crítica (alert_sfx.mp3).
 */
export function tocarSomAlerta() {
  reproduzir("alerta", 600);
}

/**
 * Toca em caso de atenção, aviso ou cuidado (caution_sfx.mp3).
 */
export function tocarSomAtencao() {
  reproduzir("atencao", 600);
}

/**
 * Toca o som correspondente ao estado/tipo informado.
 */
export function tocarSomPorTipo(tipo) {
  switch (tipo) {
    case "sucesso":
      tocarSomConfirmacao();
      break;
    case "erro":
    case "critica":
      tocarSomAlerta();
      break;
    case "atencao":
    case "aviso":
      tocarSomAtencao();
      break;
    case "notificacao":
      tocarSomNotificacao();
      break;
    default:
      break;
  }
}
