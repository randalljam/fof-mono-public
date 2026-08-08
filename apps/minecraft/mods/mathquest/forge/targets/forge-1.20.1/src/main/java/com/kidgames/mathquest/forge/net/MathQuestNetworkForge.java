package com.kidgames.mathquest.forge.net;

import com.kidgames.mathquest.forge.MathQuestForge;
import com.kidgames.mathquest.forge.entity.MathQuestNerdDespawnForge;
import com.kidgames.mathquest.forge.platform.ForgePlatformInventory;
import com.kidgames.mathquest.forge.platform.ForgePlatformNetwork;
import com.kidgames.mathquest.forge.platform.ForgePlatformPlayers;
import com.kidgames.mathquest.forge.server.ForgeQuizResultHooks;
import com.kidgames.mathquest.persistence.SqliteDriver;
import com.kidgames.mathquest.net.FluencyFeastResultData;
import com.kidgames.mathquest.net.OpenQuizData;
import com.kidgames.mathquest.platform.PlayerContext;
import com.kidgames.mathquest.config.MathQuestConfig;
import com.kidgames.mathquest.server.QuizResultProcessor;
import com.kidgames.mathquest.reward.TpCreditBank;
import com.kidgames.mathquest.reward.TpCreditCompletionTracker;
import net.minecraft.network.chat.Component;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.network.NetworkEvent;
import net.minecraftforge.network.NetworkRegistry;
import net.minecraftforge.network.PacketDistributor;
import net.minecraftforge.network.simple.SimpleChannel;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.api.distmarker.Dist;

import java.util.function.Supplier;

public final class MathQuestNetworkForge {
    private static final String PROTOCOL = "2";
    public static final SimpleChannel CHANNEL = NetworkRegistry.newSimpleChannel(
        new ResourceLocation(MathQuestForge.MOD_ID, "main"),
        () -> PROTOCOL,
        PROTOCOL::equals,
        MathQuestNetworkVersionPolicy.serverAcceptedVersions(PROTOCOL)
    );

    private static int nextId = 0;
    private static final ForgePlatformInventory PLATFORM_INVENTORY = new ForgePlatformInventory();
    private static final ForgePlatformNetwork.Server SERVER_NETWORK = new ForgePlatformNetwork.Server();

    private static final ForgeQuizResultHooks QUIZ_RESULT_HOOKS = ForgeQuizResultHooks.INSTANCE;

    private MathQuestNetworkForge() {}

    public static void register() {
        SqliteDriver.ensureLoaded();
        CHANNEL.registerMessage(nextId++, GiveRewardPacket.class, GiveRewardPacket::encode, GiveRewardPacket::decode, GiveRewardPacket::handle);
        CHANNEL.registerMessage(nextId++, QuizResultPacket.class, QuizResultPacket::encode, QuizResultPacket::decode, QuizResultPacket::handle);
        CHANNEL.registerMessage(nextId++, OpenQuizPacket.class, OpenQuizPacket::encode, OpenQuizPacket::decode, MathQuestNetworkForge::handleOpenQuizPacket);
        CHANNEL.registerMessage(nextId++, FluencyFeastResultPacket.class, FluencyFeastResultPacket::encode, FluencyFeastResultPacket::decode, MathQuestNetworkForge::handleFluencyFeastResultPacket);
        CHANNEL.registerMessage(nextId++, DespawnNerdsPacket.class, DespawnNerdsPacket::encode, DespawnNerdsPacket::decode, DespawnNerdsPacket::handle);
        CHANNEL.registerMessage(nextId++, EarnTpCreditsPacket.class, EarnTpCreditsPacket::encode, EarnTpCreditsPacket::decode, EarnTpCreditsPacket::handle);
    }

    public static void sendToServer(Object packet) {
        CHANNEL.sendToServer(packet);
    }

    public static void sendToPlayer(ServerPlayer player, Object packet) {
        CHANNEL.send(PacketDistributor.PLAYER.with(() -> player), packet);
    }

    static void handleOpenQuizPacket(OpenQuizPacket msg, Supplier<NetworkEvent.Context> ctxSupplier) {
        NetworkEvent.Context ctx = ctxSupplier.get();
        ctx.enqueueWork(() -> DistExecutor.unsafeRunWhenOn(Dist.CLIENT, () -> () ->
            MathQuestNetworkClientHandlers.handleOpenQuiz(msg)));
        ctx.setPacketHandled(true);
    }

    static void handleFluencyFeastResultPacket(FluencyFeastResultPacket msg, Supplier<NetworkEvent.Context> ctxSupplier) {
        NetworkEvent.Context ctx = ctxSupplier.get();
        ctx.enqueueWork(() -> DistExecutor.unsafeRunWhenOn(Dist.CLIENT, () -> () ->
            MathQuestNetworkClientHandlers.handleFluencyFeastResult(msg)));
        ctx.setPacketHandled(true);
    }

    public record GiveRewardPacket(String itemId, int count) {
        public static void encode(GiveRewardPacket msg, FriendlyByteBuf buf) {
            buf.writeUtf(msg.itemId);
            buf.writeVarInt(msg.count);
        }

        public static GiveRewardPacket decode(FriendlyByteBuf buf) {
            return new GiveRewardPacket(buf.readUtf(), buf.readVarInt());
        }

        public static void handle(GiveRewardPacket msg, Supplier<NetworkEvent.Context> ctxSupplier) {
            NetworkEvent.Context ctx = ctxSupplier.get();
            ctx.enqueueWork(() -> {
                ServerPlayer player = ctx.getSender();
                if (player == null) return;
                PlayerContext playerContext = ForgePlatformPlayers.fromServerPlayer(player);
                QuizResultProcessor.grantReward(
                    PLATFORM_INVENTORY,
                    playerContext,
                    new MathQuestConfig.RewardEntry(msg.itemId, msg.count)
                );
            });
            ctx.setPacketHandled(true);
        }
    }

    public record QuizResultPacket(String resultJson) {
        public static void encode(QuizResultPacket msg, FriendlyByteBuf buf) {
            buf.writeUtf(msg.resultJson);
        }

        public static QuizResultPacket decode(FriendlyByteBuf buf) {
            return new QuizResultPacket(buf.readUtf());
        }

        public static void handle(QuizResultPacket msg, Supplier<NetworkEvent.Context> ctxSupplier) {
            NetworkEvent.Context ctx = ctxSupplier.get();
            ctx.enqueueWork(() -> {
                ServerPlayer player = ctx.getSender();
                if (player == null) return;
                PlayerContext playerContext = ForgePlatformPlayers.fromServerPlayer(player);
                com.kidgames.mathquest.platform.MathQuestLog.LOGGER.info(
                    "[MathQuest/Forge] Processing quiz result from {}", player.getName().getString());
                QuizResultProcessor.process(
                    msg.resultJson,
                    playerContext,
                    PLATFORM_INVENTORY,
                    SERVER_NETWORK,
                    QUIZ_RESULT_HOOKS
                );
            });
            ctx.setPacketHandled(true);
        }
    }

    public record OpenQuizPacket(
        String operation,
        int minNumber,
        int maxNumber,
        int problemsPerQuiz,
        String problemsJson,
        String rewardsJson,
        String rewardMode,
        String quizType,
        String optionsJson,
        boolean fluencyFeastMode,
        boolean directToQuiz
    ) {
        public static OpenQuizPacket from(OpenQuizData data) {
            return new OpenQuizPacket(
                data.operation(),
                data.minNumber(),
                data.maxNumber(),
                data.problemsPerQuiz(),
                data.problemsJson(),
                data.rewardsJson(),
                data.rewardMode(),
                data.quizType(),
                data.optionsJson(),
                data.fluencyFeastMode(),
                data.directToQuiz()
            );
        }

        public OpenQuizData toData() {
            return new OpenQuizData(
                operation,
                minNumber,
                maxNumber,
                problemsPerQuiz,
                problemsJson,
                rewardsJson,
                rewardMode,
                quizType,
                optionsJson,
                fluencyFeastMode,
                directToQuiz
            );
        }

        public static void encode(OpenQuizPacket msg, FriendlyByteBuf buf) {
            buf.writeUtf(msg.operation);
            buf.writeVarInt(msg.minNumber);
            buf.writeVarInt(msg.maxNumber);
            buf.writeVarInt(msg.problemsPerQuiz);
            buf.writeUtf(msg.problemsJson);
            buf.writeUtf(msg.rewardsJson);
            buf.writeUtf(msg.rewardMode);
            buf.writeUtf(msg.quizType);
            buf.writeUtf(msg.optionsJson);
            buf.writeBoolean(msg.fluencyFeastMode);
            buf.writeBoolean(msg.directToQuiz);
        }

        public static OpenQuizPacket decode(FriendlyByteBuf buf) {
            return new OpenQuizPacket(
                buf.readUtf(),
                buf.readVarInt(),
                buf.readVarInt(),
                buf.readVarInt(),
                buf.readUtf(),
                buf.readUtf(),
                buf.readUtf(),
                buf.readUtf(),
                buf.readUtf(),
                buf.readBoolean(),
                buf.readBoolean()
            );
        }

    }

    public static OpenQuizPacket toOpenQuizPacket(OpenQuizData data) {
        return OpenQuizPacket.from(data);
    }

    public static void sendOpenQuiz(ServerPlayer player, OpenQuizData data) {
        sendToPlayer(player, OpenQuizPacket.from(data));
    }

    public static void sendFluencyFeastResult(ServerPlayer player, FluencyFeastResultData data) {
        sendToPlayer(player, new FluencyFeastResultPacket(
            data.beforePercent(),
            data.afterPercent(),
            data.rewardDescription(),
            data.rewardsJson(),
            data.rewardMode()
        ));
    }

    public record FluencyFeastResultPacket(
        int before,
        int after,
        String rewardDescription,
        String rewardsJson,
        String rewardMode
    ) {
        public static void encode(FluencyFeastResultPacket msg, FriendlyByteBuf buf) {
            buf.writeVarInt(msg.before);
            buf.writeVarInt(msg.after);
            buf.writeUtf(msg.rewardDescription == null ? "" : msg.rewardDescription);
            buf.writeUtf(msg.rewardsJson == null ? "[]" : msg.rewardsJson);
            buf.writeUtf(msg.rewardMode == null ? "all" : msg.rewardMode);
        }

        public static FluencyFeastResultPacket decode(FriendlyByteBuf buf) {
            return new FluencyFeastResultPacket(
                buf.readVarInt(),
                buf.readVarInt(),
                buf.readUtf(),
                buf.readUtf(),
                buf.readUtf()
            );
        }

    }

    public record DespawnNerdsPacket() {
        public static void encode(DespawnNerdsPacket msg, FriendlyByteBuf buf) {}

        public static DespawnNerdsPacket decode(FriendlyByteBuf buf) {
            return new DespawnNerdsPacket();
        }

        public static void handle(DespawnNerdsPacket msg, Supplier<NetworkEvent.Context> ctxSupplier) {
            NetworkEvent.Context ctx = ctxSupplier.get();
            ctx.enqueueWork(() -> {
                ServerPlayer player = ctx.getSender();
                if (player == null) return;
                MathQuestNerdDespawnForge.despawnNerdsNear(player);
            });
            ctx.setPacketHandled(true);
        }
    }

    /** One-use completion request; earning settings and amount are resolved server-side. */
    public record EarnTpCreditsPacket(String completionToken) {
        public static void encode(EarnTpCreditsPacket msg, FriendlyByteBuf buf) {
            buf.writeUtf(msg.completionToken);
        }

        public static EarnTpCreditsPacket decode(FriendlyByteBuf buf) {
            return new EarnTpCreditsPacket(buf.readUtf());
        }

        public static void handle(EarnTpCreditsPacket msg, Supplier<NetworkEvent.Context> ctxSupplier) {
            NetworkEvent.Context ctx = ctxSupplier.get();
            ctx.enqueueWork(() -> {
                ServerPlayer player = ctx.getSender();
                if (player == null) return;
                String playerName = player.getName().getString();
                if (!TpCreditCompletionTracker.consumeCompleted(playerName, msg.completionToken)) {
                    player.sendSystemMessage(Component.literal(
                        "[MathQuest] TP credits were not awarded: this quiz is incomplete, invalid, or already used."
                    ));
                    return;
                }
                MathQuestConfig config = MathQuestConfig.INSTANCE;
                TpCreditBank.AwardResult result = new TpCreditBank(config).awardCompletedQuiz(playerName);
                if (result.persistenceFailed()) {
                    player.sendSystemMessage(Component.literal("[MathQuest] TP credits could not be saved. Balance unchanged: "
                        + result.balance() + "."));
                } else if (result.awarded()) {
                    player.sendSystemMessage(Component.literal("[MathQuest] Quiz complete! Earned "
                        + result.creditsAwarded() + " TP credit" + (result.creditsAwarded() == 1 ? "" : "s")
                        + ". Balance: " + result.balance() + "."));
                } else if (config.resolveTpCreditEarningEnabled(playerName)) {
                    player.sendSystemMessage(Component.literal("[MathQuest] No TP credits earned. Balance: "
                        + result.balance() + "."));
                }
            });
            ctx.setPacketHandled(true);
        }
    }
}
