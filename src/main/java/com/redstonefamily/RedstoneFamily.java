package com.redstonefamily;

import com.mojang.logging.LogUtils;
import net.neoforged.fml.common.Mod;
import org.slf4j.Logger;

/** Common entry point for Redstone Family. */
@Mod(RedstoneFamily.MOD_ID)
public class RedstoneFamily {
    public static final String MOD_ID = "redstonefamily";
    public static final Logger LOGGER = LogUtils.getLogger();

    public RedstoneFamily() {
        LOGGER.info("Redstone Family initialized");
    }
}
